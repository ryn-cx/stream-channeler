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
from app.episodes.name_forms import plaintext_forms
from app.episodes.name_matching import similarity
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
    def translated_name_forms(self) -> dict[uuid.UUID, frozenset[str]]:
        cache: dict[uuid.UUID, frozenset[str]] = self._cache(
            "translated_episode_name_forms",
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
            tmdb.preload_episode_translations(
                [
                    numbering
                    for numbering in numberings.values()
                    if numbering is not None
                ],
            )
            for tmdb_episode in unread:
                cache[tmdb_episode.id] = self._episode_name_forms(
                    tmdb,
                    numberings[tmdb_episode.id],
                )

        return {
            tmdb_episode.id: cache[tmdb_episode.id]
            for tmdb_episode in self.canonical_episodes
        }

    # TODO: Validate
    def preload_translations(self) -> None:
        _forms = self.translated_name_forms

    # TODO: Validate
    def forms_of(self, tmdb_episode: Episode) -> frozenset[str]:
        return self.translated_name_forms.get(tmdb_episode.id, frozenset())

    # TODO: Validate
    @cached_property
    def alternate_episode_numbers(self) -> dict[uuid.UUID, frozenset[int]]:
        cache: dict[int, dict[int, frozenset[int]]] = self._cache(
            "alternate_tmdb_episode_numbers",
        )
        tmdb = self._tmdb(self.session)
        by_tmdb_id: dict[int, frozenset[int]] = {}
        for canonical_show in self.canonical_shows:
            tmdb_show_id = tmdb_id_of(canonical_show.key, SHOW_LEVEL)
            media_type = tmdb_media_type_of(canonical_show.key, SHOW_LEVEL)
            if tmdb_show_id is None or media_type is not MediaType.tv:
                continue
            if tmdb_show_id not in cache:
                cache[tmdb_show_id] = tmdb.alternate_episode_numbers(tmdb_show_id)
            by_tmdb_id |= cache[tmdb_show_id]

        alternate_numbers: dict[uuid.UUID, frozenset[int]] = {}
        for tmdb_episode in self.canonical_episodes:
            tmdb_episode_id = tmdb_id_of(tmdb_episode.key, EPISODE_LEVEL)
            if tmdb_episode_id is None:
                continue
            if numbers := by_tmdb_id.get(tmdb_episode_id):
                alternate_numbers[tmdb_episode.id] = numbers
        return alternate_numbers

    # TODO: Validate
    def alternate_numbers_of(self, tmdb_episode: Episode) -> Collection[int]:
        return self.alternate_episode_numbers.get(tmdb_episode.id, frozenset())

    # TODO: Validate
    @staticmethod
    def raw_name_similarity(episode: Episode, tmdb_episode: Episode) -> float:
        return similarity(episode.name, tmdb_episode.name)

    # TODO: Validate
    def best_name_similarity(self, episode: Episode, tmdb_episode: Episode) -> float:
        cache: dict[tuple[str | None, uuid.UUID], float] = self._cache(
            "episode_name_similarity",
        )
        cache_key = (episode.name, tmdb_episode.id)
        if (cached := cache.get(cache_key)) is not None:
            return cached

        best = similarity(episode.name, tmdb_episode.name)
        if best < 1.0:
            translated_forms = self.forms_of(tmdb_episode)
            for form in plaintext_forms(episode.name):
                for translated_form in translated_forms:
                    best = max(best, similarity(form, translated_form))
                    if best >= 1.0:
                        break
                if best >= 1.0:
                    break

        cache[cache_key] = best
        return best

    # TODO: Validate
    @staticmethod
    def _episode_numbering(tmdb_episode: Episode) -> tuple[int, int, int] | None:
        season = tmdb_episode.season
        tmdb_show_id = tmdb_id_of(season.show.key, SHOW_LEVEL)
        if (
            tmdb_show_id is None
            or season.season_number is None
            or tmdb_episode.episode_number is None
        ):
            return None
        return (tmdb_show_id, season.season_number, tmdb_episode.episode_number)

    # TODO: Validate
    @staticmethod
    def _episode_name_forms(
        tmdb: TMDB,
        numbering: tuple[int, int, int] | None,
    ) -> frozenset[str]:
        if numbering is None:
            return frozenset()
        return frozenset(
            form
            for name in tmdb.translated_episode_names(*numbering)
            for form in plaintext_forms(name)
        )
