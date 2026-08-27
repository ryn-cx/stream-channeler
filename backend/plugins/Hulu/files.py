# TODO: Validate
"""The files Hulu is read out of."""

import json
from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import cache
from typing import Any, override

from sqlmodel import Session
from wholoo import Wholoo
from wholoo.exceptions import (
    MovieNotFoundError,
    ResourceNotFoundError,
    SeriesNotFoundError,
)
from wholoo.movies import Movies as MoviesEndpoint
from wholoo.movies.models import MoviesModel
from wholoo.search import Search as SearchEndpoint
from wholoo.search.models import SearchModel
from wholoo.season import Season as SeasonEndpoint
from wholoo.season.models import Item as SeasonItem
from wholoo.season.models import SeasonModel
from wholoo.tv import TV
from wholoo.tv.models import TVModel

from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.Hulu.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointFile
from plugins.utils.base_plugin.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def wholoo() -> Wholoo:
    """Return a cached Wholoo client."""
    return Wholoo(get_around_client=get_around_client())


# The details hub for a single episode, which is the only place the id of the series
# an episode belongs to can be looked up.
# TODO: Add this to Wholoo so it has full type support.
# TODO: Validate
class EpisodeHubEndpoint:
    # TODO: Validate
    def __init__(self, client: Wholoo) -> None:
        self._client = client

    # TODO: Validate
    def download(self, episode_id: str, /) -> str:
        return self._client.download(
            endpoint=f"content/v5/hubs/episode/{episode_id}",
            params={
                "schema": "3",
                "limit": "1999",
                "device_info": "web:4.44.1",
                "referralHost": "production",
                "pageType": "DETAILS",
            },
            headers={"Referer": f"https://www.hulu.com/watch/{episode_id}"},
            log_id=f"EpisodeHub ({episode_id!r})",
        )

    # TODO: Validate
    def load(self, data: str, log_id: str = "") -> dict[str, Any]:  # noqa: ARG002
        parsed: dict[str, Any] = json.loads(data)
        return parsed


# TODO: Validate
class Series(EndpointFile[TVModel]):
    """Series file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> TV:
        return wholoo().tv

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


# TODO: Validate
class Movie(EndpointFile[MoviesModel]):
    """Movie file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> MoviesEndpoint:
        return wholoo().movies

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)


# TODO: Validate
class SeasonFile(EndpointFile[SeasonModel]):
    """Season file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> SeasonEndpoint:
        return wholoo().season

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
    def _download_file(self) -> str:
        return self._endpoint().download(self.series_id, self.season_number)


# TODO: Validate
class EpisodeHub(EndpointFile[dict[str, Any]]):
    """Episode file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> EpisodeHubEndpoint:
        return EpisodeHubEndpoint(wholoo())

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # TODO: Validate
    def series_id(self) -> str:
        """Return the id of the series the episode belongs to."""
        entity = self.parsed()["details"]["vod_items"]["focus"]["entity"]
        return str(entity["series_id"])


# TODO: Validate
class SearchFile(EndpointFile[SearchModel]):
    """Search file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> SearchEndpoint:
        return wholoo().search

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


# TODO: Validate
class FileMixin(MediaTypeMixin, BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def search_file(self, query: str) -> SearchFile:
        """Return SearchFile file."""
        return self._file(SearchFile, query)

    # TODO: Validate
    def series_file(self, series_id: str) -> Series:
        """Return Series file."""
        return self._file(Series, series_id)

    # TODO: Validate
    def episode_hub_file(self, episode_id: str) -> EpisodeHub:
        """Return EpisodeHub file."""
        return self._file(EpisodeHub, episode_id)

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
    def _series_model(self, series_id: str) -> TVModel:
        return self.series_file(series_id).parsed()

    # TODO: Validate
    def _season_numbers(self, series_id: str) -> list[int]:
        numbers: dict[int, None] = {}
        for component in self._series_model(series_id).components:
            for item in component.items:
                grouping = item.series_grouping_metadata
                if grouping is not None:
                    numbers[grouping.season_number] = None
        return sorted(numbers)

    # TODO: Validate
    def _season_items(self, series_id: str, season_number: int) -> list[SeasonItem]:
        return self.season_file(series_id, season_number).parsed().items

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
                    str(item.id) for item in self._season_items(show_key, season_number)
                ]
        return episode_keys
