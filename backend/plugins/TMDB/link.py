# TODO: Validate
import re
import unicodedata
from collections.abc import Sequence
from functools import cache
from itertools import product
from math import prod
from typing import Literal, Protocol

from pykakasi import kakasi
from pykakasi.kanji import Kanwa
from tminidb.tv_season_details.models import Episode as TvSeasonEpisode

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from plugins.TMDB.lookup import LookupMixin

_MAX_READING_COMBINATIONS = 32


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


def _find_by_name[NamedType: _Named](
    candidates: Sequence[NamedType],
    name: str | None,
) -> NamedType | None:
    if not name:
        return None

    targets = _plaintext_forms(name)
    matches = [
        candidate
        for candidate in candidates
        if _plaintext_forms(candidate.name) & targets
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
        media_type: Literal["movie", "tv"] = "tv",
    ) -> Show:
        """Point a `Show` at its TMDB title.

        The `show_identifier` is taken from TMDB whenever one is found, since it
        is what makes the same title on two websites a single title rather than
        two. TMDB numbers films and series separately, so the media type is part
        of the identifier to keep a film and a series that share a number apart.
        """
        show.tmdb_id = show.tmdb_id or tmdb_id
        if show.tmdb_id:
            show.show_identifier = f"TMDB {media_type} {show.tmdb_id}"
        return show

    def tmdb_link_season(
        self,
        season: Season,
        tmdb_id: int | None,
        season_number: int | None,
        media_type: Literal["movie", "tv"],
    ) -> Season:
        """Point a `Season` at its TMDB season.

        The `season_identifier` is taken from TMDB whenever one is found, since
        it is what makes the same season on two websites a single season rather
        than two. TMDB numbers films and seasons separately, so the media type is
        part of the identifier to keep two that share a number apart.
        """
        if not tmdb_id or season.tmdb_id:
            return season

        if media_type == "movie":
            if movie := self._movie_detail(tmdb_id):
                season.tmdb_id = movie.id
                season.season_identifier = f"TMDB movie {movie.id}"
            return season

        seasons = self.show_detail_file(tmdb_id).parsed().seasons
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
            season.tmdb_id = season_detail.id
            season.season_identifier = f"TMDB tv {season_detail.id}"
        return season

    def tmdb_link_episode(
        self,
        episode: Episode,
        tmdb_id: int | None,
        season_number: int | None,
        episode_number: int | None,
        media_type: Literal["movie", "tv"] = "tv",
    ) -> Episode:
        """Point an `Episode` at its TMDB episode.

        The `episode_identifier` is taken from TMDB whenever one is found, since
        it is what makes the same episode on two websites a single episode to
        watch rather than two. TMDB numbers films and episodes separately, so the
        media type is part of the identifier to keep two that share a number
        apart.
        """
        if not tmdb_id:
            return episode

        if media_type == "movie":
            if movie := self._movie_detail(tmdb_id):
                episode.tmdb_id = episode.tmdb_id or movie.id
                episode.episode_identifier = f"TMDB movie {movie.id}"
            return episode

        episode_detail = self._episode_detail(
            tmdb_id,
            season_number,
            episode_number,
            episode.name,
        )
        if episode_detail:
            episode.tmdb_id = episode.tmdb_id or episode_detail.id
            episode.episode_identifier = f"TMDB tv {episode_detail.id}"
        return episode

    def _episode_detail(
        self,
        tmdb_id: int,
        season_number: int | None,
        episode_number: int | None,
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        if not episode_name:
            return self._episode_by_number(tmdb_id, season_number, episode_number)

        episodes = self._all_episodes(tmdb_id)

        if episode_detail := _find_by_name(episodes, episode_name):
            return episode_detail

        return self._find_by_translated_name(tmdb_id, episodes, episode_name)

    def _find_by_translated_name(
        self,
        tmdb_id: int,
        episodes: Sequence[TvSeasonEpisode],
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        if not episode_name:
            return None

        targets = _plaintext_forms(episode_name)
        matches = [
            episode
            for episode in episodes
            if self._translated_names(tmdb_id, episode) & targets
        ]
        return matches[0] if len(matches) == 1 else None

    def _translated_names(self, tmdb_id: int, episode: TvSeasonEpisode) -> set[str]:
        translations_file = self.episode_translations_file(
            tmdb_id,
            episode.season_number,
            episode.episode_number,
        )
        return {
            form
            for translation in translations_file.parsed()
            if translation.data.name
            for form in _plaintext_forms(translation.data.name)
        }

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

        episodes = self.season_detail_file(tmdb_id, season_number).parsed().episodes
        return next(
            (
                candidate
                for candidate in episodes
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
            for season in self.show_detail_file(tmdb_id).parsed().seasons:
                season_detail = self.season_detail_file(
                    tmdb_id,
                    season.season_number,
                ).parsed()
                episodes.extend(season_detail.episodes)
            self._all_episodes_cache = episodes
        return self._all_episodes_cache
