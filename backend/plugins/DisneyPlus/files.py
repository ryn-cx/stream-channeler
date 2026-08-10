# TODO: Validate
from collections.abc import Sequence
from functools import cache
from typing import Any, override
from uuid import UUID

from kneeminus import KneeMinus
from kneeminus.entity.models import (
    DetailEntityHero,
    EntityModel,
    MediaDetails,
)
from kneeminus.entity.models import Episode as EntityEpisode
from kneeminus.entity.models import Season as EntitySeason
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import BaseFile, PartialGAPIJSON
from plugins.utils.get_around_client import get_around_client


@cache
def kneeminus() -> KneeMinus:
    return KneeMinus(get_around_client=get_around_client())


class EntityFile(PartialGAPIJSON[EntityModel]):
    """Entity file."""

    API_ENDPOINT = kneeminus().entity
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"

    def __init__(self, session: Session, plugin: Plugin, entity_id: str) -> None:
        self.entity_id = entity_id
        super().__init__(session, plugin, entity_id)

    @override
    def _get(self) -> EntityModel:
        return self.API_ENDPOINT.download_and_parse(UUID(self.entity_id))


class SeasonEntityFile(PartialGAPIJSON[EntityModel]):
    """Season entity file."""

    API_ENDPOINT = kneeminus().entity
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        entity_id: str,
        season_id: str,
    ) -> None:
        self.entity_id = entity_id
        self.season_id = season_id
        super().__init__(session, plugin, f"{entity_id}/{season_id}")

    @override
    def _get(self) -> EntityModel:
        return self.API_ENDPOINT.download_and_parse(
            UUID(self.entity_id),
            season_id=UUID(self.season_id),
        )


class FileMixin(TMDBMixin, register=False):
    def entity_file(self, entity_id: str) -> EntityFile:
        """Returns EntityFile file."""
        return self._file(EntityFile, entity_id)

    def season_file(self, entity_id: str, season_id: str) -> SeasonEntityFile:
        """Returns SeasonEntityFile file."""
        return self._file(SeasonEntityFile, entity_id, season_id)

    def _grouped(self, entity_id: str) -> EntityModel:
        return self.entity_file(entity_id).parsed()

    def _season_grouped(self, entity_id: str, season_id: str) -> EntityModel:
        return self.season_file(entity_id, season_id).parsed()

    def _media_details(self, show_key: str) -> MediaDetails:
        return self._grouped(show_key).media_details

    def _hero(self, show_key: str) -> DetailEntityHero:
        return self._grouped(show_key).detail_entity_hero

    def _is_movie(self, show_key: str) -> bool:
        return self._grouped(show_key).episodes is None

    def _seasons(self, show_key: str) -> list[EntitySeason]:
        episodes = self._grouped(show_key).episodes
        if episodes is None:
            return []
        return episodes.seasons

    def _season_episodes(self, show_key: str, season_id: str) -> list[EntityEpisode]:
        episodes = self._season_grouped(show_key, season_id).episodes
        if episodes is None:
            return []
        return episodes.episodes

    @staticmethod
    def _season_key(show_key: str, season_id: str) -> str:
        return f"{show_key}:{season_id}"

    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, str]:
        show_key, _, season_id = season_key.partition(":")
        return show_key, season_id

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file([self.entity_file(show_key)], show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie(show_key):
            base_files = [self.entity_file(show_key)]
        else:
            _, season_id = self._split_season_key(season_key)
            base_files = [self.season_file(show_key, season_id)]
        return self._append_tmdb_season_file(base_files, season_key, show_key)

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie(show_key):
            base_files = [self.entity_file(show_key)]
        else:
            _, season_id = self._split_season_key(season_key)
            base_files = [self.season_file(show_key, season_id)]
        return self._append_tmdb_episode_file(
            base_files,
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._season_key(show_key, show_key)]
        return [
            self._season_key(show_key, str(season.id))
            for season in self._seasons(show_key)
        ]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_id = self._split_season_key(season_key)
            if self._is_movie(show_key):
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    str(episode.field_id)
                    for episode in self._season_episodes(show_key, season_id)
                ]
        return episode_keys
