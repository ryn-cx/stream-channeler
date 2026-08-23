# TODO: Validate
"""The files Hulu is read out of."""

from collections.abc import Sequence
from typing import Any, override

from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.Hulu import api
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON
from plugins.utils.base_plugin.media_type import MediaTypeMixin

MOVIE_MEDIA_TYPE = "movie"
"""What Hulu calls a title that is a film rather than a series."""

SERIES_MEDIA_TYPE = "series"
"""What Hulu calls a title that is a series rather than a film."""


# TODO: Validate
class HuluJSON(EndpointJSON[dict[str, Any]]):
    """A file holding one Hulu endpoint's parsed JSON."""

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
class Series(HuluJSON):
    """Series file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.series_hub(self.unique_identifier)


# TODO: Validate
class Movie(HuluJSON):
    """Movie file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.movie_hub(self.unique_identifier)


# TODO: Validate
class SearchFile(HuluJSON):
    """Search file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.search_entity(self.unique_identifier)


# TODO: Validate
class SeasonFile(HuluJSON):
    """Season file."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        series_id: str,
        season_number: int,
    ) -> None:
        """Initialize the file."""
        self.series_id = series_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{series_id}/{season_number}")

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.season(self.series_id, self.season_number)


# The details hub for a single episode, which is the only place the id of the series
# an episode belongs to can be looked up.
# TODO: Validate
class EpisodeHub(HuluJSON):
    """Episode file."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.episode_hub(self.unique_identifier)

    # TODO: Validate
    def series_id(self) -> str:
        """Return the id of the series the episode belongs to."""
        entity = self.parsed()["details"]["vod_items"]["focus"]["entity"]
        return str(entity["series_id"])


# TODO: Validate
class FileMixin(MediaTypeMixin, BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def series_file(self, series_id: str) -> Series:
        """Return Series file."""
        return self._file(Series, series_id)

    # TODO: Validate
    def episode_hub_file(self, episode_id: str) -> EpisodeHub:
        """Return EpisodeHub file."""
        return self._file(EpisodeHub, episode_id)

    # TODO: Validate
    def search_file(self, query: str) -> SearchFile:
        """Return SearchFile file."""
        return self._file(SearchFile, query)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> Movie:
        """Return Movie file."""
        return self._file(Movie, movie_id)

    # TODO: Validate
    def season_file(self, series_id: str, season_number: int) -> SeasonFile:
        """Return SeasonFile file."""
        return self._file(SeasonFile, series_id, season_number)

    # TODO: Validate
    def _is_movie(self) -> bool:
        if self._media_type_value not in (MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)

        return self._media_type_value == MOVIE_MEDIA_TYPE

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
    def _series_data(self, series_id: str) -> dict[str, Any]:
        return self.series_file(series_id).parsed()

    # TODO: Validate
    def _season_numbers(self, series_id: str) -> list[int]:
        numbers: dict[int, None] = {}
        for component in self._series_data(series_id)["components"]:
            for item in component["items"]:
                grouping = item.get("series_grouping_metadata")
                if grouping is not None:
                    numbers[grouping["season_number"]] = None
        return sorted(numbers)

    # TODO: Validate
    def _season_items(
        self,
        series_id: str,
        season_number: int,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = self.season_file(
            series_id,
            season_number,
        ).parsed()["items"]
        return items

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        if self._is_movie():
            return [self.movie_file(show_key)]
        return [self.series_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the season and new episodes of it.
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
        return [self.season_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # An episode is read out of its season's listing, so the listing is what
        # says whether the episode has changed.
        if self._is_movie():
            return [self.movie_file(show_key)]
        _, season_number = self._split_season_key(season_key)
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
                    str(item["id"])
                    for item in self._season_items(show_key, season_number)
                ]
        return episode_keys
