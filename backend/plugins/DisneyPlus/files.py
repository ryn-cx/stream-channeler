# TODO: Validate
"""The files a Disney+ title is read out of."""

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
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, PartialGAPIJSON
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def kneeminus() -> KneeMinus:
    """Returns a cached KneeMinus client."""
    return KneeMinus(get_around_client=get_around_client())


# TODO: Validate
class EntityFile(PartialGAPIJSON[EntityModel]):
    """Entity file."""

    API_ENDPOINT = kneeminus().entity
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin, entity_id: str) -> None:
        """Initialize the file."""
        self.entity_id = entity_id
        super().__init__(session, plugin, entity_id)

    # TODO: Validate
    @override
    def _get(self) -> EntityModel:
        return self.API_ENDPOINT.download_and_parse(UUID(self.entity_id))


# TODO: Validate
class SeasonEntityFile(PartialGAPIJSON[EntityModel]):
    """Season entity file."""

    API_ENDPOINT = kneeminus().entity
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        entity_id: str,
        season_id: str,
    ) -> None:
        """Initialize the file."""
        self.entity_id = entity_id
        self.season_id = season_id
        super().__init__(session, plugin, f"{entity_id}/{season_id}")

    # TODO: Validate
    @override
    def _get(self) -> EntityModel:
        return self.API_ENDPOINT.download_and_parse(
            UUID(self.entity_id),
            season_id=UUID(self.season_id),
        )


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def entity_file(self, entity_id: str) -> EntityFile:
        """Returns EntityFile file."""
        return self._file(EntityFile, entity_id)

    # TODO: Validate
    def season_file(self, entity_id: str, season_id: str) -> SeasonEntityFile:
        """Returns SeasonEntityFile file."""
        return self._file(SeasonEntityFile, entity_id, season_id)

    # TODO: Validate
    def _grouped(self, entity_id: str) -> EntityModel:
        return self.entity_file(entity_id).parsed()

    # TODO: Validate
    def _season_grouped(self, entity_id: str, season_id: str) -> EntityModel:
        return self.season_file(entity_id, season_id).parsed()

    # TODO: Validate
    def _media_details(self, show_key: str) -> MediaDetails:
        return self._grouped(show_key).media_details

    # TODO: Validate
    def _hero(self, show_key: str) -> DetailEntityHero:
        return self._grouped(show_key).detail_entity_hero

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return self._grouped(show_key).episodes is None

    # TODO: Validate
    def _seasons(self, show_key: str) -> list[EntitySeason]:
        episodes = self._grouped(show_key).episodes
        if episodes is None:
            return []
        return episodes.seasons

    # TODO: Validate
    def _season_episodes(self, show_key: str, season_id: str) -> list[EntityEpisode]:
        episodes = self._season_grouped(show_key, season_id).episodes
        if episodes is None:
            return []
        return episodes.episodes

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_id: str) -> str:
        return f"{show_key}:{season_id}"

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, str]:
        show_key, _, season_id = season_key.partition(":")
        return show_key, season_id

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.entity_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # A movie is a season of itself, so its own page is what it is read out of.
        if self._is_movie(show_key):
            return [self.entity_file(show_key)]
        _, season_id = self._split_season_key(season_key)
        return [self.season_file(show_key, season_id)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        if self._is_movie(show_key):
            return [self.entity_file(show_key)]
        _, season_id = self._split_season_key(season_key)
        return [self.season_file(show_key, season_id)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._season_key(show_key, show_key)]
        return [
            self._season_key(show_key, str(season.id))
            for season in self._seasons(show_key)
        ]

    # TODO: Validate
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
