# TODO: Validate
"""The files Pluto TV is read out of."""

from collections.abc import Sequence
from typing import Any, override

from plugins.Pluto import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON
from plugins.utils.base_plugin.media_type import MediaTypeMixin

# A movie has no seasons of its own so its single season is given a fixed number.
_MOVIE_SEASON_NUMBER = 0


# TODO: Validate
class PlutoJSON[T: dict[str, Any] | list[dict[str, Any]]](EndpointJSON[T]):
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
class ItemsFile(PlutoJSON[list[dict[str, Any]]]):
    """Items file."""

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> list[dict[str, Any]]:
        return self.raise_if_not_is_instance(raw, list)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.PlutoItemNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        """Return what is written down in place of a title that does not exist."""
        return f"Invalid item_id {self.unique_identifier}"

    # TODO: Validate
    @override
    def _fetch(self) -> list[dict[str, Any]]:
        return api.items([self.unique_identifier])


# TODO: Validate
class SeasonsFile(PlutoJSON[dict[str, Any]]):
    """Seasons file."""

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return self.raise_if_not_is_instance(raw, dict)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.PlutoSeriesNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        """Return what is written down in place of a series that does not exist."""
        return f"Invalid series_id {self.unique_identifier}"

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.seasons(self.unique_identifier)


# TODO: Validate
class FileMixin(MediaTypeMixin, BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def items_file(self, item_id: str) -> ItemsFile:
        """Contains the metadata of a single on-demand movie."""
        return self._file(ItemsFile, item_id)

    # TODO: Validate
    def seasons_file(self, series_id: str) -> SeasonsFile:
        """Contains a series' metadata, its seasons, and all of their episodes."""
        return self._file(SeasonsFile, series_id)

    # TODO: Validate
    def _item(self, show_key: str) -> dict[str, Any]:
        return self.items_file(show_key).parsed()[0]

    # TODO: Validate
    def _series(self, show_key: str) -> dict[str, Any]:
        return self.seasons_file(show_key).parsed()

    # TODO: Validate
    def _is_movie(self) -> bool:
        if self._media_type_value not in ("movie", "series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)
        return self._media_type_value == "movie"

    # TODO: Validate
    def _seasons(self, show_key: str) -> list[dict[str, Any]]:
        seasons: list[dict[str, Any]] = self._series(show_key)["seasons"]
        return seasons

    # TODO: Validate
    def _season_episodes(
        self,
        show_key: str,
        season_number: int,
    ) -> list[dict[str, Any]]:
        for season in self._seasons(show_key):
            if season["number"] == season_number:
                episodes: list[dict[str, Any]] = season["episodes"]
                return episodes
        return []

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        """Encode the show key into the season key.

        Every entity's data comes from the single file keyed by the show, but the
        base plugin resolves episode files from a season key alone, so the show
        key is carried inside it.
        """
        return f"{show_key}:{season_number}"

    # TODO: Validate
    @classmethod
    def _movie_season_key(cls, show_key: str) -> str:
        return cls._season_key(show_key, _MOVIE_SEASON_NUMBER)

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.partition(":")
        return show_key, int(season_number)

    # TODO: Validate
    def _show_file(self, show_key: str) -> BaseFile[Any]:
        if self._is_movie():
            return self.items_file(show_key)
        return self.seasons_file(show_key)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self._show_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # The seasons and their episodes all come down with the show's own file.
        return [self._show_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self._show_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [self._movie_season_key(show_key)]
        return [
            self._season_key(show_key, season["number"])
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
            show_key, season_number = self._split_season_key(season_key)
            if self._is_movie():
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    episode["_id"]
                    for episode in self._season_episodes(show_key, season_number)
                ]
        return episode_keys
