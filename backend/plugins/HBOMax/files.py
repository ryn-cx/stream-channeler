# TODO: Validate
"""The files HBO Max is read out of."""

from collections.abc import Sequence
from typing import Any, override

from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.HBOMax import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON
from plugins.utils.base_plugin.media_type import MediaTypeMixin


# TODO: Validate
class HBOMaxJSON(EndpointJSON[dict[str, Any]]):
    """A page's __NEXT_DATA__ JSON."""

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return self.raise_if_not_is_instance(raw, dict)

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
class ShowFile(HBOMaxJSON):
    """Show file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.show(self.unique_identifier)


# TODO: Validate
class SeasonFile(HBOMaxJSON):
    """Season file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        show_id: str,
        season_number: int,
    ) -> None:
        """Initialize the file."""
        self.show_id = show_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{show_id}/{season_number}")

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.show(self.show_id, season_number=self.season_number)


# TODO: Validate
class MovieFile(HBOMaxJSON):
    """Movie file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.movie(self.unique_identifier)


# TODO: Validate
class FileMixin(MediaTypeMixin, BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def show_file(self, show_id: str) -> ShowFile:
        """Return ShowFile file."""
        return self._file(ShowFile, show_id)

    # TODO: Validate
    def season_file(self, show_id: str, season_number: int) -> SeasonFile:
        """Return SeasonFile file."""
        return self._file(SeasonFile, show_id, season_number)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        """Return MovieFile file."""
        return self._file(MovieFile, movie_id)

    # TODO: Validate
    def _is_movie(self) -> bool:
        if self._media_type_value not in ("movie", "series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)

        return self._media_type_value == "movie"

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        return f"{show_key}:{season_number}"

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.rpartition(":")
        return show_key, int(season_number)

    # TODO: Validate
    @staticmethod
    def _episode_key(season_key: str, episode_number: int) -> str:
        return f"{season_key}:{episode_number}"

    # TODO: Validate
    @staticmethod
    def _content(page: dict[str, Any]) -> dict[str, Any]:
        return api.content(page)

    # TODO: Validate
    def _show_content(self, show_id: str) -> dict[str, Any]:
        return self._content(self.show_file(show_id).parsed())

    # TODO: Validate
    def _season_numbers(self, show_id: str) -> list[int]:
        return [
            season["seasonNumber"] for season in self._show_content(show_id)["seasons"]
        ]

    # TODO: Validate
    def _season_entry(self, show_id: str, season_number: int) -> dict[str, Any]:
        for season in self._show_content(show_id)["seasons"]:
            if season["seasonNumber"] == season_number:
                return season
        msg = f"Season {season_number} not found for {show_id}"
        raise ValueError(msg)

    # TODO: Validate
    def _season_episodes(
        self,
        show_id: str,
        season_number: int,
    ) -> list[dict[str, Any]]:
        content = self._content(self.season_file(show_id, season_number).parsed())
        for season in content["seasons"]:
            if season["seasonNumber"] == season_number:
                episodes: list[dict[str, Any]] = season["episodes"]
                return episodes
        msg = f"Season {season_number} not found for {show_id}"
        raise ValueError(msg)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        # Required to detect changes to the show and new seasons of it.
        return [self.show_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        # Required to detect changes to the season and new episodes of it.
        return [self.season_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        return [self.season_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [self._season_key(show_key, 0)]
        return [
            self._season_key(show_key, season_number)
            for season_number in self._season_numbers(show_key)
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
            show_key, season_number = self._split_season_key(season_key)
            if self._is_movie():
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    self._episode_key(season_key, episode["episodeNumber"])
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
