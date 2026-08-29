# TODO: Validate

import uuid
from collections.abc import Collection, Sequence
from functools import cached_property
from typing import TYPE_CHECKING, Any

from sqlmodel import Session

from app.canonical_media.keys import (
    EPISODE_LEVEL,
    SHOW_LEVEL,
    tmdb_id_of,
    tmdb_media_type_of,
)
from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.shows.models import Show

if TYPE_CHECKING:
    from plugins.TMDB import TMDB


# TODO: Validate
class TmdbEpisodeFacts:
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        canonical_shows: Sequence[Show],
        canonical_episodes: Sequence[Episode],
    ) -> None:
        self.session = session
        self.canonical_shows = canonical_shows
        self.canonical_episodes = canonical_episodes

    # TODO: Validate
    def _cache(self, name: str) -> dict[Any, Any]:
        cache: dict[Any, Any] = self.session.info.setdefault(name, {})
        return cache

    # TODO: Validate
    @staticmethod
    def _tmdb(session: Session) -> TMDB:
        from plugins.TMDB import TMDB  # noqa: PLC0415

        return TMDB(session)

    # TODO: Validate
    @cached_property
    def translated_names(self) -> dict[uuid.UUID, tuple[str, ...]]:
        cache: dict[uuid.UUID, tuple[str, ...]] = self._cache(
            "translated_episode_names",
        )
        unread = [
            tmdb_episode
            for tmdb_episode in self.canonical_episodes
            if tmdb_episode.id not in cache
        ]
        if unread:
            tmdb = self._tmdb(self.session)
            numberings = {
                tmdb_episode.id: self._episode_numbering(tmdb_episode)
                for tmdb_episode in unread
            }
            movie_ids = {
                tmdb_episode.id: self._movie_id(tmdb_episode) for tmdb_episode in unread
            }
            tmdb.preload_episode_translations(
                [
                    numbering
                    for numbering in numberings.values()
                    if numbering is not None
                ],
            )
            tmdb.preload_movie_translations(
                [movie_id for movie_id in movie_ids.values() if movie_id is not None],
            )
            for tmdb_episode in unread:
                cache[tmdb_episode.id] = self._names(
                    tmdb,
                    numberings[tmdb_episode.id],
                    movie_ids[tmdb_episode.id],
                )

        return {
            tmdb_episode.id: cache[tmdb_episode.id]
            for tmdb_episode in self.canonical_episodes
        }

    # TODO: Validate
    def names_of(self, tmdb_episode: Episode) -> tuple[str, ...]:
        names = [tmdb_episode.name] if tmdb_episode.name else []
        names.extend(self.translated_names.get(tmdb_episode.id, ()))
        return tuple(dict.fromkeys(name.strip() for name in names if name.strip()))

    # TODO: Validate
    @cached_property
    def alternate_episode_numbers(self) -> dict[uuid.UUID, dict[int, frozenset[str]]]:
        cache: dict[int, dict[int, dict[int, frozenset[str]]]] = self._cache(
            "alternate_tmdb_episode_numbers",
        )
        tmdb = self._tmdb(self.session)
        by_tmdb_id: dict[int, dict[int, frozenset[str]]] = {}
        for canonical_show in self.canonical_shows:
            tmdb_show_id = tmdb_id_of(canonical_show.key, SHOW_LEVEL)
            media_type = tmdb_media_type_of(canonical_show.key, SHOW_LEVEL)
            if tmdb_show_id is None or media_type is not MediaType.tv:
                continue
            if tmdb_show_id not in cache:
                cache[tmdb_show_id] = tmdb.alternate_episode_numbers(tmdb_show_id)
            by_tmdb_id |= cache[tmdb_show_id]

        alternate_numbers: dict[uuid.UUID, dict[int, frozenset[str]]] = {}
        for tmdb_episode in self.canonical_episodes:
            tmdb_episode_id = tmdb_id_of(tmdb_episode.key, EPISODE_LEVEL)
            if tmdb_episode_id is None:
                continue
            if numbers := by_tmdb_id.get(tmdb_episode_id):
                alternate_numbers[tmdb_episode.id] = numbers
        return alternate_numbers

    # TODO: Validate
    def alternate_numbers_of(self, tmdb_episode: Episode) -> Collection[int]:
        return self.alternate_episode_numbers.get(tmdb_episode.id, {}).keys()

    # TODO: Validate
    def alternate_order_names_of(
        self,
        tmdb_episode: Episode,
        episode_number: int,
    ) -> Collection[str]:
        numbers = self.alternate_episode_numbers.get(tmdb_episode.id, {})
        return numbers.get(episode_number, frozenset())

    # TODO: Validate
    @staticmethod
    def _episode_numbering(tmdb_episode: Episode) -> tuple[int, int, int] | None:
        from plugins.TMDB.episode_groups import parse_episode_extra  # noqa: PLC0415

        native = parse_episode_extra(tmdb_episode.extra)
        season = tmdb_episode.season
        if tmdb_media_type_of(season.show.key, SHOW_LEVEL) is not MediaType.tv:
            return None
        tmdb_show_id = tmdb_id_of(season.show.key, SHOW_LEVEL)
        season_number = (
            native.tmdb_season_number
            if native.tmdb_season_number is not None
            else season.season_number
        )
        episode_number = (
            native.tmdb_episode_number
            if native.tmdb_episode_number is not None
            else tmdb_episode.episode_number
        )
        if tmdb_show_id is None or season_number is None or episode_number is None:
            return None
        return (tmdb_show_id, season_number, episode_number)

    # TODO: Validate
    @staticmethod
    def _movie_id(tmdb_episode: Episode) -> int | None:
        show = tmdb_episode.season.show
        if tmdb_media_type_of(show.key, SHOW_LEVEL) is not MediaType.movie:
            return None
        return tmdb_id_of(show.key, SHOW_LEVEL)

    # TODO: Validate
    @staticmethod
    def _names(
        tmdb: TMDB,
        numbering: tuple[int, int, int] | None,
        movie_id: int | None,
    ) -> tuple[str, ...]:
        if numbering is not None:
            return tuple(tmdb.translated_episode_names(*numbering))
        if movie_id is not None:
            return tuple(tmdb.translated_movie_names(movie_id))
        return ()
