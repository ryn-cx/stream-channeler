# TODO: Validate
import re
import unicodedata
from collections.abc import Callable, Sequence
from difflib import SequenceMatcher
from functools import cache
from itertools import product
from math import prod
from typing import NamedTuple, Protocol

from pykakasi import kakasi
from pykakasi.kanji import Kanwa
from tminidb.tv_season_details.models import Episode as TvSeasonEpisode

from app.episodes.models import (
    DESCRIPTION_NOTE,
    NAME_AND_NUMBER_NOTE,
    Episode,
)
from app.media.identifiers import tmdb_identifier
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from plugins.TMDB.lookup import LookupMixin

_MAX_READING_COMBINATIONS = 32
_GENERIC_EPISODE_NAME = re.compile(r"episode\s*\d+")


class _Named(Protocol):
    name: str


def _plaintext(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


@cache
def _converter() -> kakasi:
    return kakasi()


@cache
def _kanwa() -> Kanwa:
    return Kanwa()


def _hepburn(text: str) -> str:
    return "".join(part["hepburn"] for part in _converter().convert(text))


def _readings(segment: str) -> frozenset[str]:
    table = _kanwa().load(segment[0]) or {}
    return frozenset(reading for reading, _context in table.get(segment, []))


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


def _unmarked(plaintext_name: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", plaintext_name)
        if not unicodedata.combining(character)
    )


def _folded(plaintext_name: str) -> str:
    without_long_vowels = re.sub(
        r"([aeiou])\1+",
        r"\1",
        _unmarked(plaintext_name).replace("ou", "o"),
    )
    return re.sub(r"m(?=[bmp])", "n", without_long_vowels)


def _plaintext_forms(name: str) -> frozenset[str]:
    plaintext = _plaintext(name)
    forms = {plaintext, _folded(plaintext)}

    for romanization in _romanizations(name):
        romanized = _plaintext(romanization)
        if romanized != plaintext:
            forms |= {romanized, _folded(romanized)}

    return frozenset(form for form in forms if form)


def _is_generically_named(name: str) -> bool:
    return bool(_GENERIC_EPISODE_NAME.fullmatch(name.strip().casefold()))


type _Compare = Callable[[frozenset[str], frozenset[str]], bool]

# What an episode was recognised by, said in the words it is shown in. Only the
# first two are sure enough to settle a link; the rest say how a guess was made.
_NAME_NOTE = "Named the same"
_TRANSLATED_NAME_NOTE = "Named the same in another language"
_PARTIAL_NAME_NOTE = "One name contains the other"
_PARTIAL_TRANSLATED_NAME_NOTE = "One name contains the other in another language"
_NUMBER_ONLY_NOTE = "Numbered the same, with no name to go on"
_SAME_LENGTH_SEASON_NOTE = "Numbered the same, in a season of the same length"
_CLOSEST_NAME_AND_NUMBER_NOTE = "Closest name of the title, and the number agrees"


class _EpisodeMatch(NamedTuple):
    """The TMDB episode a website's episode is, and what it was recognised by."""

    episode: TvSeasonEpisode
    note: str


def _matches_exactly(candidate_forms: frozenset[str], targets: frozenset[str]) -> bool:
    return bool(candidate_forms & targets)


def _contains_either_way(
    candidate_forms: frozenset[str],
    targets: frozenset[str],
) -> bool:
    return any(
        candidate_form in target or target in candidate_form
        for candidate_form, target in product(candidate_forms, targets)
    )


def _similarity(name: str | None, other_name: str | None) -> float:
    """Return how much of two names is the same, from nothing to all of it."""
    if not name or not other_name:
        return 0.0
    plaintext = _plaintext(name)
    other_plaintext = _plaintext(other_name)
    if not plaintext or not other_plaintext:
        return 0.0
    if plaintext in other_plaintext or other_plaintext in plaintext:
        return 1.0
    return SequenceMatcher(None, plaintext, other_plaintext).ratio()


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


def _find_by_description(
    candidates: Sequence[TvSeasonEpisode],
    description: str | None,
) -> TvSeasonEpisode | None:
    """Return the one episode described word for word as `description`.

    A website that takes its descriptions from TMDB carries the very text TMDB
    wrote, which says which episode it is more surely than a name does: a name
    gets translated, shortened and rewritten on the way, where a description
    long enough to be worth copying is copied whole. Two episodes described the
    same way say nothing about which of them it is, so neither is returned.
    """
    if not description:
        return None

    target = _plaintext(description)
    if not target:
        return None

    matches = [
        candidate
        for candidate in candidates
        if _plaintext(candidate.overview) == target
    ]
    return matches[0] if len(matches) == 1 else None


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


class LinkMixin(LookupMixin, register=False):
    """Points a plugin's own media at the TMDB media standing in for it.

    Only the ids and the `episode_identifier` are stored. Everything a website
    leaves out is read off the linked TMDB record when the media is served, so
    it follows TMDB without the stored record having to be rewritten.
    """

    def tmdb_link_show(
        self,
        show: Show,
        tmdb_id: int | None,
        media_type: MediaType = MediaType.tv,
    ) -> Show:
        """Point a `Show` at its TMDB title.

        The `show_identifier` is taken from TMDB whenever one is found, since it
        is what makes the same title on two websites a single title rather than
        two, and it is the only place the TMDB id is kept. A title already linked
        keeps the id it has, so a fresh guess never displaces one.
        """
        linked_id = show.tmdb_id or tmdb_id
        if linked_id:
            show.show_identifier = tmdb_identifier(media_type, linked_id)
        return show

    def tmdb_link_season(
        self,
        season: Season,
        tmdb_id: int | None,
        season_number: int | None,
        media_type: MediaType,
    ) -> Season:
        """Point a `Season` at its TMDB season.

        The `season_identifier` is taken from TMDB whenever one is found, since
        it is what makes the same season on two websites a single season rather
        than two. TMDB numbers films and seasons separately, so the media type is
        part of the identifier to keep two that share a number apart.
        """
        if not tmdb_id or season.tmdb_id:
            return season

        if media_type == MediaType.movie:
            if movie := self._movie_detail(tmdb_id):
                season.season_identifier = tmdb_identifier(MediaType.movie, movie.id)
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
            season.season_identifier = tmdb_identifier(MediaType.tv, season_detail.id)
        return season

    def tmdb_link_episode(  # noqa: PLR0913 - Every part of what names a TMDB episode.
        self,
        episode: Episode,
        tmdb_id: int | None,
        season_number: int | None,
        episode_number: int | None,
        media_type: MediaType = MediaType.tv,
        highest_episode_number: int | None = None,
    ) -> Episode:
        """Point an `Episode` at its TMDB episode.

        The `episode_identifier` is taken from TMDB whenever one is found, since
        it is what makes the same episode on two websites a single episode to
        watch rather than two. TMDB numbers films and episodes separately, so the
        media type is part of the identifier to keep two that share a number
        apart.

        `highest_episode_number` is the last episode number the website gives
        the season. A season the website and TMDB both end on the same number is
        one neither has split or merged, so its numbering can be trusted, and it
        is what an episode whose name matched nothing falls back on.
        """
        if not tmdb_id:
            return episode

        if media_type == MediaType.movie:
            if movie := self._movie_detail(tmdb_id):
                episode.episode_identifier = tmdb_identifier(
                    MediaType.movie,
                    episode.tmdb_id or movie.id,
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
            episode.episode_identifier = tmdb_identifier(
                MediaType.tv,
                episode.tmdb_id or match.episode.id,
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
            episode.episode_identifier_note = settled or match.note
            episode.episode_identifier_locked = settled is not None
        return episode

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

        described = _find_by_description(
            self._all_episodes(tmdb_id),
            episode.description,
        )
        if described is not None and described.id == episode_detail.id:
            return DESCRIPTION_NOTE
        return None

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
        # Tried ahead of the name because a description is only ever this exact
        # when it came from TMDB itself, which names the episode outright, and
        # because it answers for the episodes whose names say nothing.
        if described := _find_by_description(self._all_episodes(tmdb_id), description):
            return _EpisodeMatch(described, DESCRIPTION_NOTE)

        if not episode_name or _is_generically_named(episode_name):
            numbered = self._episode_by_number(tmdb_id, season_number, episode_number)
            return _EpisodeMatch(numbered, _NUMBER_ONLY_NOTE) if numbered else None

        if match := self._exactly_named(tmdb_id, episode_name):
            return _EpisodeMatch(match, _NAME_NOTE)

        if match := self._exactly_named_in_translation(tmdb_id, episode_name):
            return _EpisodeMatch(match, _TRANSLATED_NAME_NOTE)

        if match := self._exact_substring(tmdb_id, episode_name):
            return _EpisodeMatch(match, _PARTIAL_NAME_NOTE)

        if match := self._named_within_translation(tmdb_id, episode_name):
            return _EpisodeMatch(match, _PARTIAL_TRANSLATED_NAME_NOTE)

        if match := self._numbered_the_same_way(
            tmdb_id,
            season_number,
            episode_number,
            highest_episode_number,
        ):
            return _EpisodeMatch(match, _SAME_LENGTH_SEASON_NOTE)

        if match := self._closest_name_the_number_agrees_with(
            tmdb_id,
            episode_number,
            episode_name,
        ):
            return _EpisodeMatch(match, _CLOSEST_NAME_AND_NUMBER_NOTE)
        return None

    def _closest_name_the_number_agrees_with(
        self,
        tmdb_id: int,
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
        if not episode_name or episode_number is None:
            return None

        episodes = self._all_episodes(tmdb_id)
        if not episodes:
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

    def _exactly_named(
        self,
        tmdb_id: int,
        episode_name: str,
    ) -> TvSeasonEpisode | None:
        return _find_by_name(
            self._all_episodes(tmdb_id),
            episode_name,
            _matches_exactly,
        )

    def _exactly_named_in_translation(
        self,
        tmdb_id: int,
        episode_name: str,
    ) -> TvSeasonEpisode | None:
        return self._find_by_translated_name(
            tmdb_id,
            self._all_episodes(tmdb_id),
            episode_name,
            _matches_exactly,
        )

    def _exact_substring(
        self,
        tmdb_id: int,
        episode_name: str,
    ) -> TvSeasonEpisode | None:
        return _find_by_name(
            self._all_episodes(tmdb_id),
            episode_name,
            _contains_either_way,
        )

    def _named_within_translation(
        self,
        tmdb_id: int,
        episode_name: str,
    ) -> TvSeasonEpisode | None:
        return self._find_by_translated_name(
            tmdb_id,
            self._all_episodes(tmdb_id),
            episode_name,
            _contains_either_way,
        )

    def _numbered_the_same_way(
        self,
        tmdb_id: int,
        season_number: int | None,
        episode_number: int | None,
        highest_episode_number: int | None,
    ) -> TvSeasonEpisode | None:
        if not self._season_ends_on_the_same_number(
            tmdb_id,
            season_number,
            highest_episode_number,
        ):
            return None

        return self._episode_by_number(tmdb_id, season_number, episode_number)

    def _season_ends_on_the_same_number(
        self,
        tmdb_id: int,
        season_number: int | None,
        highest_episode_number: int | None,
    ) -> bool:
        if season_number is None or highest_episode_number is None:
            return False
        if not self.has_season(tmdb_id, season_number):
            return False

        episodes = self._season_episodes(tmdb_id, season_number)
        tmdb_numbers = [episode.episode_number for episode in episodes]
        if not tmdb_numbers:
            return False
        return max(tmdb_numbers) == highest_episode_number

    def _find_by_translated_name(
        self,
        tmdb_id: int,
        episodes: Sequence[TvSeasonEpisode],
        episode_name: str | None,
        compare: _Compare = _matches_exactly,
    ) -> TvSeasonEpisode | None:
        if not episode_name:
            return None

        targets = _plaintext_forms(episode_name)
        matches = [
            episode
            for episode in episodes
            if compare(self._translated_names(tmdb_id, episode), targets)
        ]
        return matches[0] if len(matches) == 1 else None

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

    def _episode_by_number(
        self,
        tmdb_id: int,
        season_number: int | None,
        episode_number: int | None,
    ) -> TvSeasonEpisode | None:
        if not season_number or not episode_number:
            return None
        if not self.has_season(tmdb_id, season_number):
            return None

        return next(
            (
                candidate
                for candidate in self._season_episodes(tmdb_id, season_number)
                if candidate.episode_number == episode_number
            ),
            None,
        )

    _all_episodes_cache: list[TvSeasonEpisode] | None = None

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
