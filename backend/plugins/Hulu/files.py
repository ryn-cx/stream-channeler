# TODO: Validate
from collections.abc import Sequence
from functools import cache
from typing import Any, cast, override

from sqlmodel import Session
from wholoo import Wholoo
from wholoo.movies.models import MoviesModel
from wholoo.search.models import SearchModel
from wholoo.season.models import Item as SeasonItem
from wholoo.season.models import SeasonModel
from wholoo.tv.models import TVModel

from app.plugins.models import Plugin
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import (
    GAPIJSON,
    BaseFile,
    JSONFile,
    PartialGAPIJSON,
)
from plugins.utils.base_plugin.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client


@cache
def wholoo() -> Wholoo:
    return Wholoo(get_around_client=get_around_client())


# The details hub for a single episode, which is the only place the id of the series
# an episode belongs to can be looked up.
_EPISODE_HUB_URL = "https://discover.hulu.com/content/v5/hubs/episode"
_EPISODE_HUB_PARAMS = {
    "schema": "3",
    "limit": "1999",
    "device_info": "web:4.44.1",
    "referralHost": "production",
    "pageType": "DETAILS",
}


class Series(GAPIJSON[TVModel]):
    """Series file."""

    API_ENDPOINT = wholoo().tv


class Movie(GAPIJSON[MoviesModel]):
    """Movie file."""

    API_ENDPOINT = wholoo().movies


class SearchFile(GAPIJSON[SearchModel]):
    """Search file."""

    API_ENDPOINT = wholoo().search


class SeasonFile(PartialGAPIJSON[SeasonModel]):
    """Season file."""

    API_ENDPOINT = wholoo().tv.season

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        series_id: str,
        season_number: int,
    ) -> None:
        self.series_id = series_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{series_id}/{season_number}")

    @override
    def _get(self) -> SeasonModel:
        return self.API_ENDPOINT.download_and_parse(self.series_id, self.season_number)


class EpisodeHub(JSONFile[dict[str, Any]]):
    """Episode file."""

    # TODO: Add this to Wholoo so it has full type support.
    def __init__(self, session: Session, plugin: Plugin, episode_id: str) -> None:
        self.unique_identifier = episode_id
        super().__init__(session, plugin)

    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            self.write(
                wholoo().download(
                    f"{_EPISODE_HUB_URL}/{self.unique_identifier}",
                    f"https://www.hulu.com/watch/{self.unique_identifier}",
                    params=_EPISODE_HUB_PARAMS,
                    log_id=f"EpisodeHub/{self.unique_identifier}",
                ),
            )

    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return cast("dict[str, Any]", raw)

    def series_id(self) -> str:
        """Return the id of the series the episode belongs to."""
        entity = self.parsed()["details"]["vod_items"]["focus"]["entity"]
        return str(entity["series_id"])


class FileMixin(MediaTypeMixin, TMDBMixin, register=False):
    def series_file(self, series_id: str) -> Series:
        """Returns Series file."""
        return self._file(Series, series_id)

    def episode_hub_file(self, episode_id: str) -> EpisodeHub:
        """Returns EpisodeHub file."""
        return self._file(EpisodeHub, episode_id)

    def search_file(self, query: str) -> SearchFile:
        """Returns SearchFile file."""
        return self._file(SearchFile, query)

    def movie_file(self, movie_id: str) -> Movie:
        """Returns Movie file."""
        return self._file(Movie, movie_id)

    def season_file(self, series_id: str, season_number: int) -> SeasonFile:
        """Returns SeasonFile file."""
        return self._file(SeasonFile, series_id, season_number)

    def _is_movie(self) -> bool:
        if self._media_type_value not in ("movie", "series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)

        return self._media_type_value == "movie"

    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        return f"{show_key}:{season_number}"

    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.rpartition(":")
        return show_key, int(season_number)

    def _series_model(self, series_id: str) -> TVModel:
        return self.series_file(series_id).parsed()

    def _season_numbers(self, series_id: str) -> list[int]:
        numbers: dict[int, None] = {}
        for component in self._series_model(series_id).components:
            for item in component.items:
                grouping = item.series_grouping_metadata
                if grouping is not None:
                    numbers[grouping.season_number] = None
        return sorted(numbers)

    def _season_items(self, series_id: str, season_number: int) -> list[SeasonItem]:
        return self.season_file(series_id, season_number).parsed().items

    def _season_name(self, series_id: str, season_number: int) -> str:
        parsed = self.season_file(series_id, season_number).parsed()
        return parsed.series_grouping_metadata.grouping_name

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.movie_file(show_key)]
        else:
            base_files = [self.series_file(show_key)]
        return self._append_tmdb_show_file(base_files, show_key)

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.movie_file(show_key)]
        else:
            _, season_number = self._split_season_key(season_key)
            base_files = [self.season_file(show_key, season_number)]
        return self._append_tmdb_season_file(base_files, season_key, show_key)

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.movie_file(show_key)]
        else:
            _, season_number = self._split_season_key(season_key)
            base_files = [self.season_file(show_key, season_number)]
        return self._append_tmdb_episode_file(
            base_files,
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [self._season_key(show_key, 0)]
        return [
            self._season_key(show_key, season_number)
            for season_number in self._season_numbers(show_key)
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
            show_key, season_number = self._split_season_key(season_key)
            if self._is_movie():
                episode_keys.append(show_key)
            else:
                episode_keys += [
                    str(item.id) for item in self._season_items(show_key, season_number)
                ]
        return episode_keys
