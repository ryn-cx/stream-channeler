# TODO: Validate
import re
import unicodedata
from collections.abc import Callable, Sequence
from difflib import SequenceMatcher
from functools import cache, partial
from itertools import product
from math import prod
from typing import NamedTuple, Protocol

from pykakasi import kakasi
from pykakasi.kanji import Kanwa
from tminidb.tv_season_details.models import Episode as TvSeasonEpisode

from app.canonical_media.service import (
    canonical_episode_for,
    canonical_season_for,
    canonical_show_for,
    link_canonical_show,
)
from app.episodes.models import (
    DESCRIPTION_NOTE,
    NAME_AND_NUMBER_NOTE,
    Episode,
)
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from plugins.TMDB.lookup import LookupMixin

_MAX_READING_COMBINATIONS = 32
_GENERIC_EPISODE_NAME = re.compile(r"episode\s*\d+")


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
class LinkMixin(LookupMixin, register=False):
    """Points a plugin's own media at the media it is a copy of.

    A record TMDB has an entry for is pointed at the one canonical row standing
    for that entry, which is what makes the same episode on two websites a
    single episode to watch. Everything a website leaves out is read off that
    row when the media is served, so a copy follows it without ever being
    rewritten.

    A lookup that finds nothing leaves the copy pointing where it already
    pointed, so a TMDB outage cannot quietly unlink a library. Unlinking is an
    explicit act, and `confirm_no_tmdb_match` is what performs it.
    """

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
            if movie := self._movie_detail(tmdb_id):
                season.canonical_season = canonical_season_for(
                    self.session,
                    MediaType.movie,
                    movie.id,
                    canonical_show_id,
                )
            return season

        seasons = self._show_seasons(tmdb_id)
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
            if movie := self._movie_detail(tmdb_id):
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
            for name in self.translated_episode_names(
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
        caching a show re-reads all of its season files once per episode. The
        list is dropped by `_reset_show_state` when the instance moves to
        another show, so it is held for one show rather than kept per id.
        """
        if self._all_episodes_cache is None:
            episodes: list[TvSeasonEpisode] = []
            for season in self._show_seasons(tmdb_id):
                episodes.extend(self._season_episodes(tmdb_id, season.season_number))
            self._all_episodes_cache = episodes
        return self._all_episodes_cache
