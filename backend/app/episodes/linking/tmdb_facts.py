# TODO: Validate

import uuid
from collections.abc import Collection, Sequence
from functools import cached_property
from typing import TYPE_CHECKING, Any

from sqlmodel import Session

from app.canonical_media.tmdb import (
    get_tmdb_id,
    parse_tmdb_key,
)
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.titles.models import Title

if TYPE_CHECKING:
    from plugins.TMDB.linking import TMDBLinking


# TODO: Validate
class TmdbEpisodeFacts:
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        canonical_titles: Sequence[Title],
        canonical_episodes: Sequence[Episode],
    ) -> None:
        self.session = session
        self.canonical_titles = canonical_titles
        self.canonical_episodes = canonical_episodes

    # TODO: Validate
    def preload(self) -> None:
        _ = self.alternate_episode_numbers

    # TODO: Validate
    def _cache(self, name: str) -> dict[Any, Any]:
        cache: dict[Any, Any] = self.session.info.setdefault(name, {})
        return cache

    # TODO: Validate
    @staticmethod
    def _tmdb(session: Session) -> TMDBLinking:
        from plugins.TMDB.linking import TMDBLinking  # noqa: PLC0415

        return TMDBLinking(session)

    # TODO: Validate
    def names_of(self, tmdb_episode: Episode) -> tuple[str, ...]:
        name = tmdb_episode.name.strip() if tmdb_episode.name else ""
        return (name,) if name else ()

    # TODO: Validate
    @cached_property
    def alternate_episode_numbers(self) -> dict[uuid.UUID, dict[int, frozenset[str]]]:
        cache: dict[int, dict[int, dict[int, frozenset[str]]]] = self._cache(
            "alternate_tmdb_episode_numbers",
        )
        tmdb = self._tmdb(self.session)
        by_tmdb_id: dict[int, dict[int, frozenset[str]]] = {}
        for canonical_title in self.canonical_titles:
            media_type, tmdb_title_id = parse_tmdb_key(canonical_title.key)
            if media_type is not TMDBMediaType.tv:
                continue
            if tmdb_title_id not in cache:
                cache[tmdb_title_id] = tmdb.alternate_episode_numbers(tmdb_title_id)
            by_tmdb_id |= cache[tmdb_title_id]

        alternate_numbers: dict[uuid.UUID, dict[int, frozenset[str]]] = {}
        for tmdb_episode in self.canonical_episodes:
            tmdb_episode_id = get_tmdb_id(tmdb_episode.key)
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
