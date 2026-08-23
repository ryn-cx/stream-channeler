# TODO: Validate
"""The files a Tubi title is read out of."""

from collections.abc import Sequence
from typing import Any, override

from plugins.Tubi import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON

# The `type` field of a Tubi content response marks a series; a movie and a single
# episode both use "v".
_SERIES_TYPE = "s"

# A movie has no seasons of its own so its single season is given a fixed id.
_MOVIE_SEASON_ID = "0"


# TODO: Validate
class TubiJSON(EndpointJSON[dict[str, Any]]):
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
class ContentFile(TubiJSON):
    """Content file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.content(self.unique_identifier)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.TubiContentNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid content_id {self.unique_identifier}"


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def content_file(self, content_id: str) -> ContentFile:
        """Contains all of a Tubi title's data (title, seasons, episodes)."""
        return self._file(ContentFile, content_id)

    # TODO: Validate
    def _content(self, content_id: str) -> dict[str, Any]:
        return self.content_file(content_id).parsed()

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        content_type: str = self._content(show_key)["type"]
        return content_type != _SERIES_TYPE

    # TODO: Validate
    def _seasons(self, show_key: str) -> list[dict[str, Any]]:
        children = self._content(show_key).get("children")
        if children is None:
            return []
        # Tubi returns the seasons in an arbitrary order.
        return sorted(children, key=lambda season: int(season["id"]))

    # TODO: Validate
    def _season_episodes(self, show_key: str, season_id: str) -> list[dict[str, Any]]:
        for season in self._seasons(show_key):
            if season["id"] == season_id:
                episodes: list[dict[str, Any]] = season["children"]
                return episodes
        return []

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_id: str) -> str:
        """Encode the show key into the season key.

        Every entity's data comes from the single content file keyed by the show,
        but the base plugin resolves episode files from a season key alone, so the
        show key is carried inside it.
        """
        return f"{show_key}:{season_id}"

    # TODO: Validate
    @classmethod
    def _movie_season_key(cls, show_key: str) -> str:
        return cls._season_key(show_key, _MOVIE_SEASON_ID)

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, str]:
        show_key, _, season_id = season_key.partition(":")
        return show_key, season_id

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # Every season is listed inside the show's own file, so that file is what
        # says whether a season read out of it has changed.
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.content_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._movie_season_key(show_key)]
        return [
            self._season_key(show_key, season["id"])
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
                    episode["id"]
                    for episode in self._season_episodes(show_key, season_id)
                ]
        return episode_keys
