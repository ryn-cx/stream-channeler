# TODO: Validate
"""The files The Roku Channel is read out of.

One endpoint covers every kind of content, so a movie, a series, a season and an
episode are all read out of the same file under an id of their own.
"""

from abc import ABC
from collections.abc import Sequence
from typing import Any, override
from uuid import UUID

from plugins.Roku import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON

MOVIE_TYPE = "movie"
SERIES_TYPE = "series"


# TODO: Validate
def content_id(value: str | UUID) -> str:
    """Return a Roku content id as the 32 character string the API uses."""
    return value.hex if isinstance(value, UUID) else value


# TODO: Validate
class RokuJSON(EndpointJSON[dict[str, Any]], ABC):
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
class BaseContentFile(RokuJSON, ABC):
    """What every file read off the content endpoint has in common."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.content(self.unique_identifier)


# TODO: Validate
class ContentFile(BaseContentFile):
    """Content file."""

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.RokuContentNotFoundError)


# TODO: Validate
class SeasonEpisodesFile(BaseContentFile):
    """Season episodes file."""


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def content_file(self, content_key: str) -> ContentFile:
        """Return ContentFile file."""
        return self._file(ContentFile, content_key)

    # TODO: Validate
    def season_episodes_file(self, episode_key: str) -> SeasonEpisodesFile:
        """Return SeasonEpisodesFile file."""
        return self._file(SeasonEpisodesFile, episode_key)

    # TODO: Validate
    def _content(self, content_key: str) -> dict[str, Any]:
        return self.content_file(content_key).parsed()

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        content_type: str = self._content(show_key)["type"]
        if content_type not in (MOVIE_TYPE, SERIES_TYPE):
            msg = f"Invalid media type: {content_type}"
            raise RuntimeError(msg)
        return content_type == MOVIE_TYPE

    # TODO: Validate
    def _show_episodes(self, show_key: str) -> list[dict[str, Any]]:
        return self._content(show_key).get("episodes") or []

    # TODO: Validate
    def _season_numbers(self, show_key: str) -> list[int]:
        season_numbers: list[int] = []
        for episode in self._show_episodes(show_key):
            season_number = int(episode["seasonNumber"])
            if season_number not in season_numbers:
                season_numbers.append(season_number)
        return season_numbers

    # TODO: Validate
    def _first_episode_key(self, show_key: str, season_number: int) -> str:
        for episode in self._show_episodes(show_key):
            if int(episode["seasonNumber"]) == season_number:
                return content_id(episode["meta"]["id"])
        msg = f"No episodes for season {season_number} of {show_key}."
        raise ValueError(msg)

    # TODO: Validate
    def _season_episodes(
        self,
        show_key: str,
        season_number: int,
    ) -> list[dict[str, Any]]:
        episode_key = self._first_episode_key(show_key, season_number)
        season = self.season_episodes_file(episode_key).parsed().get("season")
        if season is None:
            return []
        episodes: list[dict[str, Any]] = season["episodes"]
        return episodes

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
    def _season_episodes_files(
        self,
        season_key: str,
        show_key: str,
    ) -> list[BaseFile[Any]]:
        if self._is_movie(show_key):
            return [self.content_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        episode_key = self._first_episode_key(show_key, season_number)
        return [self.season_episodes_file(episode_key)]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._season_episodes_files(season_key, show_key)

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._season_episodes_files(season_key, show_key)

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
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
            if self._is_movie(show_key):
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    content_id(episode["meta"]["id"])
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
