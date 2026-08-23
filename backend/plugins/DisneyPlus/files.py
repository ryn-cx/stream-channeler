# TODO: Validate
"""The files a Disney+ title is read out of."""

from collections.abc import Sequence
from typing import Any, override

from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.DisneyPlus import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON


# TODO: Validate
class DisneyPlusJSON(EndpointJSON[dict[str, Any]]):
    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return api.group_main_content(self.raise_if_not_is_instance(raw, dict))

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._fetch()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_extra_value())
            else:
                self.write(response)


# TODO: Validate
class EntityFile(DisneyPlusJSON):
    """Entity file."""

    # TODO: Validate
    @override
    def _get_ACCEPTABLE_ERROR(self) -> str | None:
        return "Unexpected response status code: 404"

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin, entity_id: str) -> None:
        """Initialize the file."""
        self.entity_id = entity_id
        super().__init__(session, plugin, entity_id)

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.entity(self.entity_id)


# TODO: Validate
class SeasonEntityFile(DisneyPlusJSON):
    """Season entity file."""

    # TODO: Validate
    @override
    def _get_ACCEPTABLE_ERROR(self) -> str | None:
        return "Unexpected response status code: 404"

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
    def _fetch(self) -> dict[str, Any]:
        return api.entity(self.entity_id, season_id=self.season_id)


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def entity_file(self, entity_id: str) -> EntityFile:
        """Return EntityFile file."""
        return self._file(EntityFile, entity_id)

    # TODO: Validate
    def season_file(self, entity_id: str, season_id: str) -> SeasonEntityFile:
        """Return SeasonEntityFile file."""
        return self._file(SeasonEntityFile, entity_id, season_id)

    # TODO: Validate
    def _grouped(self, entity_id: str) -> dict[str, Any]:
        return self.entity_file(entity_id).parsed()

    # TODO: Validate
    def _season_grouped(self, entity_id: str, season_id: str) -> dict[str, Any]:
        return self.season_file(entity_id, season_id).parsed()

    # TODO: Validate
    def _media_details(self, show_key: str) -> dict[str, Any]:
        details: dict[str, Any] = self._grouped(show_key)["MediaDetails"]
        return details

    # TODO: Validate
    def _hero(self, show_key: str) -> dict[str, Any]:
        hero: dict[str, Any] = self._grouped(show_key)["DetailEntityHero"]
        return hero

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return self._grouped(show_key).get("Episodes") is None

    # TODO: Validate
    def _seasons(self, show_key: str) -> list[dict[str, Any]]:
        episodes = self._grouped(show_key).get("Episodes")
        if episodes is None:
            return []
        seasons: list[dict[str, Any]] = episodes["seasons"]
        return seasons

    # TODO: Validate
    def _season_episodes(
        self,
        show_key: str,
        season_id: str,
    ) -> list[dict[str, Any]]:
        episodes = self._season_grouped(show_key, season_id).get("Episodes")
        if episodes is None:
            return []
        season_episodes: list[dict[str, Any]] = episodes["episodes"]
        return season_episodes

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
            self._season_key(show_key, str(season["id"]))
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
                    str(episode["_id"])
                    for episode in self._season_episodes(show_key, season_id)
                ]
        return episode_keys
