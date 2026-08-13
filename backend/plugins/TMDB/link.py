# TODO: Validate
import re
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from difflib import SequenceMatcher
from functools import cache, partial
from itertools import product
from math import prod
from typing import NamedTuple, Protocol

from pykakasi import kakasi
from pykakasi.kanji import Kanwa
from sqlmodel import Session, col, select
from tminidb.tv_season_details.models import Episode as TvSeasonEpisode

from app.canonical_media.keys import SHOW_LEVEL, parse_tmdb_key
from app.canonical_media.service import (
    canonical_episode_for,
    canonical_season_for,
    canonical_show_for,
    link_canonical_show,
    sync_canonical_show,
)
from app.episodes.models import (
    DESCRIPTION_NOTE,
    NAME_AND_NUMBER_NOTE,
    Episode,
)
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.TMDB import TMDB
from plugins.TMDB.unshare import unshare_canonical_episodes

_MAX_READING_COMBINATIONS = 32
_GENERIC_EPISODE_NAME = re.compile(r"episode\s*\d+")

# What a search across the whole catalogue can turn up that is media rather than
# a person. TMDB names them on each result, so a search that was not narrowed to
# one half reads which half it landed in off the match itself.
_SEARCHED_MEDIA_TYPES = {
    "movie": MediaType.movie,
    "tv": MediaType.tv,
}


# TODO: Validate
class Media(NamedTuple):
    """One title TMDB holds: which half of the catalogue, and its id."""

    media_type: MediaType
    tmdb_id: int


# TODO: Validate
def highest_episode_number(numbers: Iterable[int | None]) -> int | None:
    """Return the last episode number a season runs to, ignoring unnumbered ones."""
    return max((number for number in numbers if number is not None), default=None)


# TODO: Validate
class _Named(Protocol):
    name: str


# TODO: Validate
def _plaintext(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


# TODO: Validate
@cache
def _converter() -> kakasi:
    return kakasi()


# TODO: Validate
@cache
def _kanwa() -> Kanwa:
    return Kanwa()


# TODO: Validate
def _hepburn(text: str) -> str:
    return "".join(part["hepburn"] for part in _converter().convert(text))


# TODO: Validate
def _readings(segment: str) -> frozenset[str]:
    table = _kanwa().load(segment[0]) or {}
    return frozenset(reading for reading, _context in table.get(segment, []))


# TODO: Validate
@cache
def _romanizations(name: str) -> frozenset[str]:
    readings_per_segment = [
        frozenset({part["hira"], *_readings(part["orig"])})
        for part in _converter().convert(name)
    ]
    if prod(len(readings) for readings in readings_per_segment) > (
        _MAX_READING_COMBINATIONS
    ):
        return frozenset({_hepburn(name)})

    return frozenset(
        _hepburn("".join(combination)) for combination in product(*readings_per_segment)
    )


# TODO: Validate
def _unmarked(plaintext_name: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", plaintext_name)
        if not unicodedata.combining(character)
    )


# TODO: Validate
def _folded(plaintext_name: str) -> str:
    without_long_vowels = re.sub(
        r"([aeiou])\1+",
        r"\1",
        _unmarked(plaintext_name).replace("ou", "o"),
    )
    return re.sub(r"m(?=[bmp])", "n", without_long_vowels)


# TODO: Validate
def _plaintext_forms(name: str) -> frozenset[str]:
    plaintext = _plaintext(name)
    forms = {plaintext, _folded(plaintext)}

    for romanization in _romanizations(name):
        romanized = _plaintext(romanization)
        if romanized != plaintext:
            forms |= {romanized, _folded(romanized)}

    return frozenset(form for form in forms if form)


# TODO: Validate
def _is_generically_named(name: str) -> bool:
    return bool(_GENERIC_EPISODE_NAME.fullmatch(name.strip().casefold()))


type _Compare = Callable[[frozenset[str], frozenset[str]], bool]
type _TranslatedNames = Callable[[TvSeasonEpisode], frozenset[str]]

# What an episode was recognised by, said in the words it is shown in. Only the
# first two are sure enough to settle a link; the rest say how a guess was made.
_NAME_NOTE = "Automatic: Named the same"
_TRANSLATED_NAME_NOTE = "Automatic: Named the same in another language"
_PARTIAL_NAME_NOTE = "Automatic: One name contains the other"
_PARTIAL_TRANSLATED_NAME_NOTE = (
    "Automatic: One name contains the other in another language"
)
_NUMBER_ONLY_NOTE = "Automatic: Numbered the same, with no name to go on"
_SAME_LENGTH_SEASON_NOTE = (
    "Automatic: Numbered the same, in a season of the same length"
)
_CLOSEST_NAME_AND_NUMBER_NOTE = (
    "Automatic: Closest name of the title, and the number agrees"
)


# TODO: Validate
class _EpisodeMatch(NamedTuple):
    """The TMDB episode a website's episode is, and what it was recognised by."""

    episode: TvSeasonEpisode
    note: str


# TODO: Validate
def _matches_exactly(candidate_forms: frozenset[str], targets: frozenset[str]) -> bool:
    return bool(candidate_forms & targets)


# TODO: Validate
def _contains_either_way(
    candidate_forms: frozenset[str],
    targets: frozenset[str],
) -> bool:
    return any(
        candidate_form in target or target in candidate_form
        for candidate_form, target in product(candidate_forms, targets)
    )


# TODO: Validate
def _similarity(name: str | None, other_name: str | None) -> float:
    """Return how much of two names is the same, from nothing to all of it."""
    if not name or not other_name:
        return 0.0
    plaintext = _plaintext(name)
    other_plaintext = _plaintext(other_name)
    if not plaintext or not other_plaintext:
        return 0.0

    ratio = SequenceMatcher(None, plaintext, other_plaintext).ratio()
    if plaintext not in other_plaintext and other_plaintext not in plaintext:
        return ratio

    # One name sitting inside the other is worth only as much of the longer name
    # as it covers. A name of a letter or two is inside almost every other name,
    # and reading as a perfect match against the whole catalogue says nothing
    # about which episode it is. Never below what the names share outright, so
    # containment can only ever help.
    shorter, longer = sorted((plaintext, other_plaintext), key=len)
    return max(ratio, len(shorter) / len(longer))


# TODO: Validate
def _absolute_numbers(episodes: Sequence[TvSeasonEpisode]) -> dict[int, int]:
    """Count a title's episodes from its first, and return that count by TMDB id.

    A website that numbers a title straight through names an episode by how far
    into the title it is rather than by how far into its own season, which is
    what makes the same episode `S3E2` on one site and `27` on another. Specials
    are outside the count, so they are left out of it rather than given a place.
    """
    ordered = sorted(
        (episode for episode in episodes if episode.season_number),
        key=lambda episode: (episode.season_number, episode.episode_number),
    )
    return {episode.id: number for number, episode in enumerate(ordered, start=1)}


# TODO: Validate
def _find_by_name[NamedType: _Named](
    candidates: Sequence[NamedType],
    name: str | None,
    compare: _Compare = _matches_exactly,
) -> NamedType | None:
    if not name:
        return None

    targets = _plaintext_forms(name)
    matches = [
        candidate
        for candidate in candidates
        if compare(_plaintext_forms(candidate.name), targets)
    ]
    return matches[0] if len(matches) == 1 else None


# TODO: Validate
class _Match:
    """Every way an episode is recognised, in one place and in no order.

    Each is only what it is handed: the title's episodes and what the website
    says about the one being linked. Which of them is worth trusting over which
    is `_episode_detail`'s to say rather than anything here.
    """

    # TODO: Validate
    @staticmethod
    def name_and_number(
        episodes: Sequence[TvSeasonEpisode],
        season_number: int | None,
        episode_number: int | None,
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        """Return the episode both the name and the numbering point at.

        Either on its own is worth less than the two together, so the episode at
        the number is only taken when the name it carries is the same one, which
        is the same agreement `_lock_reason` settles a link on.
        """
        if not episode_name or _is_generically_named(episode_name):
            return None
        numbered = _Match.number(episodes, season_number, episode_number)
        if numbered is None or not numbered.name:
            return None
        if not _matches_exactly(
            _plaintext_forms(numbered.name),
            _plaintext_forms(episode_name),
        ):
            return None
        return numbered

    # TODO: Validate
    @staticmethod
    def number(
        episodes: Sequence[TvSeasonEpisode],
        season_number: int | None,
        episode_number: int | None,
    ) -> TvSeasonEpisode | None:
        """Return the episode filed at a season and episode number."""
        if not season_number or not episode_number:
            return None
        return next(
            (
                candidate
                for candidate in episodes
                if candidate.season_number == season_number
                and candidate.episode_number == episode_number
            ),
            None,
        )

    # TODO: Validate
    @staticmethod
    def name(
        episodes: Sequence[TvSeasonEpisode],
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        """Return the one episode named exactly as the website names it."""
        return _find_by_name(episodes, episode_name, _matches_exactly)

    # TODO: Validate
    @staticmethod
    def partial_name(
        episodes: Sequence[TvSeasonEpisode],
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        """Return the one episode whose name contains the website's, or is inside it."""
        return _find_by_name(episodes, episode_name, _contains_either_way)

    # TODO: Validate
    @staticmethod
    def translated_name(
        episodes: Sequence[TvSeasonEpisode],
        episode_name: str | None,
        translated_names: _TranslatedNames,
        compare: _Compare = _matches_exactly,
    ) -> TvSeasonEpisode | None:
        """Return the one episode named this way in any language TMDB holds.

        An episode's translations are the one thing about a TMDB episode that is
        not stored alongside it, so they are handed in rather than reached for.
        """
        if not episode_name:
            return None

        targets = _plaintext_forms(episode_name)
        matches = [
            episode
            for episode in episodes
            if compare(translated_names(episode), targets)
        ]
        return matches[0] if len(matches) == 1 else None

    # TODO: Validate
    @staticmethod
    def partial_translated_name(
        episodes: Sequence[TvSeasonEpisode],
        episode_name: str | None,
        translated_names: _TranslatedNames,
    ) -> TvSeasonEpisode | None:
        """Return the one episode a translated name contains, or sits inside."""
        return _Match.translated_name(
            episodes,
            episode_name,
            translated_names,
            _contains_either_way,
        )

    # TODO: Validate
    @staticmethod
    def description(
        episodes: Sequence[TvSeasonEpisode],
        description: str | None,
    ) -> TvSeasonEpisode | None:
        """Return the one episode described word for word as `description`.

        A website that takes its descriptions from TMDB carries the very text
        TMDB wrote, which says which episode it is more surely than a name does:
        a name gets translated, shortened and rewritten on the way, where a
        description long enough to be worth copying is copied whole. Two
        episodes described the same way say nothing about which of them it is,
        so neither is returned.
        """
        if not description:
            return None

        target = _plaintext(description)
        if not target:
            return None

        matches = [
            episode for episode in episodes if _plaintext(episode.overview) == target
        ]
        return matches[0] if len(matches) == 1 else None

    # TODO: Validate
    @staticmethod
    def same_length_season_and_episode_number(
        episodes: Sequence[TvSeasonEpisode],
        season_number: int | None,
        episode_number: int | None,
        highest_episode_number: int | None,
    ) -> TvSeasonEpisode | None:
        """Return the episode at the number, when the season is as long as TMDB's.

        A number means what the website meant by it only while the two are
        counting the same episodes, which a season ending on the same number is
        the sign of.
        """
        if season_number is None or highest_episode_number is None:
            return None
        numbers = [
            episode.episode_number
            for episode in episodes
            if episode.season_number == season_number
        ]
        if not numbers or max(numbers) != highest_episode_number:
            return None
        return _Match.number(episodes, season_number, episode_number)

    # TODO: Validate
    @staticmethod
    def closest_name_and_number(
        episodes: Sequence[TvSeasonEpisode],
        episode_number: int | None,
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        """Return the closest named episode, but only where its number agrees too.

        The last thing tried, for the episodes every surer way has passed over. A
        name that only half matches is not enough to go on and a number by itself
        is not either, but the closest name in the whole title landing on the very
        number the website gives the episode is the two of them agreeing, and two
        weak signs pointing at the same episode are worth taking.

        Either numbering counts, since a website that never restarts its count
        names the episode by how far into the title it is rather than by how far
        into its season.
        """
        if not episode_name or episode_number is None or not episodes:
            return None

        similarity, closest = max(
            (
                (_similarity(episode_name, episode.name), episode)
                for episode in episodes
            ),
            key=lambda scored: scored[0],
        )
        if not similarity:
            return None
        if closest.episode_number == episode_number:
            return closest
        if _absolute_numbers(episodes).get(closest.id) == episode_number:
            return closest
        return None


# TODO: Validate
class TMDBLinker:
    """Points a plugin's own media at the media it is a copy of.

    A record TMDB has an entry for is pointed at the one canonical row standing
    for that entry, which is what makes the same episode on two websites a
    single episode to watch. Everything a website leaves out is read off that
    row when the media is served, so a copy follows it without ever being
    rewritten.

    A lookup that finds nothing leaves the copy pointing where it already
    pointed, so a TMDB outage cannot quietly unlink a library. Unlinking is an
    explicit act, and `confirm_no_tmdb_match` is what performs it.

    Not a plugin and not a mixin: any plugin builds one for its session and
    hands it the records it has just written. Downloading TMDB's files and
    upserting its canonical rows is the TMDB plugin's, reached through `tmdb`,
    so none of that lives here or in the plugin being linked.
    """

    # TODO: Validate
    def __init__(self, session: Session) -> None:
        self.session = session
        self.tmdb = TMDB(session)

    # TODO: Validate
    def search_media(
        self,
        name: str,
        media_type: MediaType | None = None,
        year: int | None = None,
    ) -> Media | None:
        """Return the media TMDB lists under a name, or None.

        `media_type` narrows the search to one half of TMDB's catalogue when the
        caller knows which it wants. Without one both halves are searched and
        whichever matches the name best is taken, which is also the only way a
        listing whose plugin cannot say what it holds is ever matched.

        A search across both halves turns up people as well as media. A person
        is not something to be a copy of, so they are passed over rather than
        taken as the best match.
        """
        if media_type is not None:
            narrowed = (
                self.tmdb.auto_updating_search_media(media_type, name, year)
                .parsed()
                .results
            )
            return Media(media_type, narrowed[0].id) if narrowed else None

        results = (
            self.tmdb.auto_updating_search_media(None, name, year).parsed().results
        )
        return next(
            (
                Media(found, result.id)
                for result in results
                if (found := _SEARCHED_MEDIA_TYPES.get(result.media_type)) is not None
            ),
            None,
        )

    # TODO: Validate
    def known_media(
        self,
        show: Show,
        media_type: MediaType | None = None,
        canonical_show: Show | None = None,
    ) -> Media | None:
        """Return the media this listing is already known to be, or None.

        A caller that named it is answered first, then the listing's own stored
        title, then a title another copy of the same listing resolved. Only when
        all three come up empty does anything have to go looking, which is a
        search against TMDB and worth not repeating.

        Which half of the catalogue the media is in is read back off whatever
        answered rather than taken from the caller, since a stored title says so
        in its own key.
        """
        supplied = self.supplied_media(media_type, canonical_show)
        if supplied is not None:
            return supplied
        own = self._linked_media(show)
        if own is not None:
            return own
        return next(
            (
                sibling
                for sibling in map(self._linked_media, self._siblings(show))
                if sibling is not None
            ),
            None,
        )

    # TODO: Validate
    def _siblings(self, show: Show) -> Sequence[Show]:
        """Return the other copies of the same listing this plugin holds.

        A plugin can hold one listing under more than one `Source` - a title
        sold on several services - and every copy of it is the same title, so
        one copy having worked out which title that is answers for all of them.
        """
        return self.session.exec(
            select(Show)
            .join(Source)
            .where(
                Show.key == show.key,
                Source.plugin_id == show.source.plugin_id,
                col(Show.id) != show.id,
            ),
        ).all()

    # TODO: Validate
    @staticmethod
    def _linked_media(show: Show) -> Media | None:
        """Return the media a stored copy is already pointed at."""
        canonical_show = show.canonical_show
        if canonical_show is None:
            return None
        parsed = parse_tmdb_key(canonical_show.key, SHOW_LEVEL)
        return None if parsed is None else Media(*parsed)

    # TODO: Validate
    @staticmethod
    def supplied_media(
        media_type: MediaType | None,
        canonical_show: Show | None,
    ) -> Media | None:
        """Return the media a caller named, when it is what this listing is.

        A caller naming a title from the other half of TMDB's catalogue is
        naming something else the listing is also a copy of - the film a series
        listing carries alongside its seasons - so the listing still has to find
        its own title for itself. Only what the listing is chiefly of is
        answered here; the title itself is linked either way. A caller that said
        nothing about which half the listing is in is taken at their word.
        """
        if canonical_show is None:
            return None
        parsed = parse_tmdb_key(canonical_show.key, SHOW_LEVEL)
        if parsed is None:
            return None
        supplied = Media(*parsed)
        if media_type is not None and supplied.media_type != media_type:
            return None
        return supplied

    # TODO: Validate
    def title_to_hand_off(
        self,
        media_type: MediaType,
        tmdb_id: int | None,
        canonical_show: Show | None,
    ) -> Show | None:
        """Return the title to tell another plugin about when handing an import on.

        The title the import started at when there is one, since that is the one
        the whole chain is working from and the one a listing further down may
        turn out to carry alongside its own. Otherwise this listing's own title,
        read in so that there is a row to name rather than only an id.
        """
        if canonical_show is not None:
            return canonical_show
        if tmdb_id is None:
            return None
        return self.tmdb.import_title(media_type, tmdb_id)

    # TODO: Validate
    def link(
        self,
        show: Show,
        media_type: MediaType | None = None,
        canonical_show: Show | None = None,
    ) -> None:
        """Leave a whole upserted listing pointing at the media it is a copy of.

        Which media the listing is of is worked out here. A caller that already
        holds the title says so with `canonical_show` and nothing is searched
        for; otherwise it is whatever the listing or another copy of it already
        resolved, and failing that TMDB is searched under the show's own name
        and year, which imports the title as canonical media.

        `media_type` only narrows that lookup, for a plugin whose own branch
        already knows whether it is holding a film or a series. Without one both
        halves of the catalogue are searched and whichever matches best is
        taken. A listing that is of neither - a channel, an artist - is not
        searched for at all, and its plugin calls `reconcile` instead.

        Linking waits until every season and episode of the listing has been
        written, since what an episode is matched to is decided partly by what
        the rest of the listing turned out to be: the season's last episode
        number says whether its numbering can be trusted, and that is only known
        once all of them are there. Doing it in one pass at the end also means a
        record the import left alone as up to date is still linked, rather than
        only the ones that happened to be rewritten.

        A `User`'s own choice is left as it is, which the upsert cannot protect
        because the linking happens after it rather than on the way in.
        """
        found = self.known_media(show, media_type, canonical_show)
        if found is None and show.name is not None:
            found = self.search_media(show.name, media_type, show.year)
        if found is not None:
            self._link_listing(show, found.media_type, found.tmdb_id)

        self.sync_canonical_info(show)

    # TODO: Validate
    def sync_canonical_info(self, show: Show) -> None:
        """Sync the Canonical media tables with the information from this Show."""
        unshare_canonical_episodes(self.session, show)
        # Whose copy this is decides whether the metadata may be written, and
        # the show says so itself rather than the caller having to repeat it.
        sync_canonical_show(self.session, show, show.source.plugin.key)

    # TODO: Validate
    def _link_listing(
        self,
        show: Show,
        media_type: MediaType,
        tmdb_id: int | None,
    ) -> None:
        """Point every record of the listing at the TMDB media it is.

        Every TMDB file the matching reads is downloaded by the lookup that
        reads it, so the whole of TMDB's side of this is fetched as it is
        needed rather than listed among the plugin's own files.
        """
        if not show.canonical_show_locked:
            self.tmdb_link_show(show, tmdb_id, media_type)
        if show.tmdb_id:
            self.tmdb.import_title(media_type, show.tmdb_id)

        for season in show.active_children:
            self.tmdb_link_season(
                season,
                show,
                season.season_number,
                media_type,
                tmdb_id,
            )
            last_episode_number = highest_episode_number(
                episode.episode_number for episode in season.active_children
            )
            for episode in season.active_children:
                if episode.canonical_episode_locked:
                    continue
                self.tmdb_link_episode(
                    episode,
                    season,
                    episode.episode_number,
                    media_type,
                    last_episode_number,
                    tmdb_id,
                )

    # TODO: Validate
    def tmdb_link_show(
        self,
        show: Show,
        tmdb_id: int | None,
        media_type: MediaType = MediaType.tv,
    ) -> Show:
        """Point a `Show` at the title TMDB holds for it.

        A title already linked keeps the id it has, so a fresh guess never
        displaces one. An id the caller names that the copy is not already linked
        to is added to the titles it is a copy of rather than dropped: a website
        that files two titles under one listing is a copy of both, and being told
        about the second is the only way that is ever learnt.
        """
        linked_id = show.tmdb_id or tmdb_id
        if linked_id:
            # The relationship rather than the id, so `show.tmdb_id` reads the
            # title straight away instead of the stale one still loaded.
            show.canonical_show = canonical_show_for(
                self.session,
                media_type,
                linked_id,
            )
            link_canonical_show(self.session, show, show.canonical_show)
        if tmdb_id and tmdb_id != linked_id:
            link_canonical_show(
                self.session,
                show,
                canonical_show_for(self.session, media_type, tmdb_id),
            )
        return show

    # TODO: Validate
    def tmdb_link_season(
        self,
        season: Season,
        show: Show,
        season_number: int | None,
        media_type: MediaType,
        tmdb_id: int | None = None,
    ) -> Season:
        """Point a `Season` at the season TMDB holds for it.

        TMDB numbers films and seasons separately, so the media type is part of
        what names the season, to keep two that share a number apart.

        The `Show` is passed in rather than read off the season, since a season
        being written for the first time is not attached to its show yet.

        `tmdb_id` is the title the import is working on, which is not always the
        title the listing is chiefly of: a listing that mixes titles is imported
        one title at a time, and the season belongs under whichever of them
        brought it in. Falls back on the listing's own title, which is the answer
        for every listing that mixes nothing.
        """
        tmdb_id = tmdb_id or show.tmdb_id
        if not tmdb_id or season.tmdb_id:
            return season

        canonical_show = canonical_show_for(self.session, media_type, tmdb_id)
        link_canonical_show(self.session, show, canonical_show)
        canonical_show_id = canonical_show.id

        if media_type == MediaType.movie:
            if movie := self.tmdb.movie_detail(tmdb_id):
                season.canonical_season = canonical_season_for(
                    self.session,
                    MediaType.movie,
                    movie.id,
                    canonical_show_id,
                )
            return season

        seasons = self.tmdb.show_seasons(tmdb_id)
        season_detail = next(
            (
                candidate
                for candidate in seasons
                if candidate.season_number == season_number
            ),
            None,
        )
        if season_detail is None:
            season_detail = _find_by_name(seasons, season.name)
        if season_detail:
            season.canonical_season = canonical_season_for(
                self.session,
                MediaType.tv,
                season_detail.id,
                canonical_show_id,
            )
        return season

    # TODO: Validate
    def tmdb_link_episode(  # noqa: PLR0913 - Every part of what names one.
        self,
        episode: Episode,
        season: Season,
        episode_number: int | None,
        media_type: MediaType = MediaType.tv,
        highest_episode_number: int | None = None,
        tmdb_id: int | None = None,
    ) -> Episode:
        """Point an `Episode` at the episode TMDB holds for it.

        TMDB numbers films and episodes separately, so the media type is part of
        what names the episode, to keep two that share a number apart.

        The `Season` is passed in rather than read off the episode, since an
        episode being written for the first time is not attached to its season
        yet.

        `highest_episode_number` is the last episode number the website gives
        the season. A season the website and TMDB both end on the same number is
        one neither has split or merged, so its numbering can be trusted, and it
        is what an episode whose name matched nothing falls back on.

        `tmdb_id` is the title the import is working on, for a listing that mixes
        titles; without one the listing's own title is what the episode is looked
        for in.
        """
        tmdb_id = tmdb_id or season.show.tmdb_id
        if not tmdb_id:
            return episode

        season_number = season.season_number
        canonical_season_id = season.canonical_season_id
        if canonical_season_id is None:
            return episode

        if media_type == MediaType.movie:
            if movie := self.tmdb.movie_detail(tmdb_id):
                episode.canonical_episode = canonical_episode_for(
                    self.session,
                    MediaType.movie,
                    episode.tmdb_id or movie.id,
                    canonical_season_id,
                )
            return episode

        match = self._episode_detail(
            tmdb_id,
            season_number,
            episode_number,
            episode.name,
            highest_episode_number,
            description=episode.description,
        )
        if match:
            episode.canonical_episode = canonical_episode_for(
                self.session,
                MediaType.tv,
                episode.tmdb_id or match.episode.id,
                canonical_season_id,
            )
            # A match sure enough to settle says so in place of how it was made,
            # which is the same thing said with more behind it.
            settled = self._lock_reason(
                tmdb_id,
                episode,
                match.episode,
                season_number,
                episode_number,
            )
            episode.canonical_episode_note = settled or match.note
            episode.canonical_episode_locked = settled is not None
        return episode

    # TODO: Validate
    def _lock_reason(
        self,
        tmdb_id: int,
        episode: Episode,
        episode_detail: TvSeasonEpisode,
        season_number: int | None,
        episode_number: int | None,
    ) -> str | None:
        """Return why the link is sure enough that no `User` need be asked.

        There are two ways of being that sure, and which one it was is returned
        rather than only that it was one of them, since a lock is worth as much
        as the grounds it was made on. The website and TMDB put the same name at
        the same number, or the website carries the very description TMDB wrote
        and only one TMDB episode carries it, which is a description copied from
        the episode itself rather than one that merely reads alike.
        """
        if self._agrees_on_name_and_number(
            episode,
            episode_detail,
            season_number,
            episode_number,
        ):
            return NAME_AND_NUMBER_NOTE

        described = _Match.description(
            self._all_episodes(tmdb_id),
            episode.description,
        )
        if described is not None and described.id == episode_detail.id:
            return DESCRIPTION_NOTE
        return None

    # TODO: Validate
    @staticmethod
    def _agrees_on_name_and_number(
        episode: Episode,
        episode_detail: TvSeasonEpisode,
        season_number: int | None,
        episode_number: int | None,
    ) -> bool:
        """Report whether the website and TMDB agree on both the name and number.

        A website that puts the same name at the same number as TMDB is
        describing the same episode as plainly as it ever will, so the link is
        settled and there is nothing left for a `User` to be asked about.
        """
        if season_number is None or episode_number is None:
            return False
        if (episode_detail.season_number, episode_detail.episode_number) != (
            season_number,
            episode_number,
        ):
            return False
        if not episode.name or not episode_detail.name:
            return False
        return _matches_exactly(
            _plaintext_forms(episode_detail.name),
            _plaintext_forms(episode.name),
        )

    # PLR0911 - One return per way of naming an episode, tried in order of trust.
    # TODO: Validate
    def _episode_detail(  # noqa: PLR0911, PLR0913 - Every part of what names one.
        self,
        tmdb_id: int,
        season_number: int | None,
        episode_number: int | None,
        episode_name: str | None,
        highest_episode_number: int | None,
        *,
        description: str | None = None,
    ) -> _EpisodeMatch | None:
        """Return the TMDB episode this one is, and what it was recognised by.

        Each way of recognising an episode is tried in the order it is worth
        trusting, and the one that answered is said along with the episode. A
        match nothing settles is still worth saying how it was made, since that
        is most of what anyone looking at it later has to go on.
        """
        episodes = self._all_episodes(tmdb_id)
        translated_names = partial(self._translated_names, tmdb_id)

        if match := _Match.name_and_number(
            episodes,
            season_number,
            episode_number,
            episode_name,
        ):
            return _EpisodeMatch(match, NAME_AND_NUMBER_NOTE)

        # If the episode name is useless just hope that the season and episode number
        # are enough for a match.
        if not episode_name or _is_generically_named(episode_name):
            numbered = _Match.number(episodes, season_number, episode_number)
            return _EpisodeMatch(numbered, _NUMBER_ONLY_NOTE) if numbered else None

        if match := _Match.name(episodes, episode_name):
            return _EpisodeMatch(match, _NAME_NOTE)

        if match := _Match.translated_name(episodes, episode_name, translated_names):
            return _EpisodeMatch(match, _TRANSLATED_NAME_NOTE)

        if match := _Match.description(episodes, description):
            return _EpisodeMatch(match, DESCRIPTION_NOTE)

        # if match := _Match.partial_name(episodes, episode_name):
        #     return _EpisodeMatch(match, _PARTIAL_NAME_NOTE)

        # if match := _Match.partial_translated_name(
        #     episodes,
        #     episode_name,
        #     translated_names,
        # ):
        #     return _EpisodeMatch(match, _PARTIAL_TRANSLATED_NAME_NOTE)

        if match := _Match.closest_name_and_number(
            episodes,
            episode_number,
            episode_name,
        ):
            return _EpisodeMatch(match, _CLOSEST_NAME_AND_NUMBER_NOTE)

        if match := _Match.same_length_season_and_episode_number(
            episodes,
            season_number,
            episode_number,
            highest_episode_number,
        ):
            return _EpisodeMatch(match, _SAME_LENGTH_SEASON_NOTE)

        return None

    # TODO: Validate
    def _translated_names(
        self,
        tmdb_id: int,
        episode: TvSeasonEpisode,
    ) -> frozenset[str]:
        return frozenset(
            form
            for name in self.tmdb.translated_episode_names(
                tmdb_id,
                episode.season_number,
                episode.episode_number,
            )
            for form in _plaintext_forms(name)
        )

    _all_episodes_cache: list[TvSeasonEpisode] | None = None

    # TODO: Validate
    def _all_episodes(self, tmdb_id: int) -> list[TvSeasonEpisode]:
        """Return every episode of the show the instance is working on.

        Every episode of a show looks its name up in the same list, so without
        caching a show re-reads all of its season files once per episode. A
        linker is built for the show being linked and let go of with it, so the
        list is held for one show rather than kept per id.
        """
        if self._all_episodes_cache is None:
            episodes: list[TvSeasonEpisode] = []
            for season in self.tmdb.show_seasons(tmdb_id):
                episodes.extend(
                    self.tmdb.season_episodes(tmdb_id, season.season_number)
                )
            self._all_episodes_cache = episodes
        return self._all_episodes_cache
