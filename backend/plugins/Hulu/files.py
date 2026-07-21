# TODO: Validate
from collections.abc import Sequence
from functools import cache
from typing import Any, override

from sqlmodel import Session
from wholoo import Wholoo
from wholoo.movies.models import MoviesModel
from wholoo.search.models import SearchModel
from wholoo.season.models import Item as SeasonItem
from wholoo.season.models import SeasonModel
from wholoo.tv.models import TVModel

from app.plugins.models import Plugin
from app.shows.models import Show
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, PartialGAPIJSON
from plugins.utils.get_around_client import get_around_client


@cache
def wholoo() -> Wholoo:
    return Wholoo(get_around_client=get_around_client())


class Series(GAPIJSON[TVModel]):
    API_ENDPOINT = wholoo().tv


class Movie(GAPIJSON[MoviesModel]):
    API_ENDPOINT = wholoo().movies


class SearchFile(GAPIJSON[SearchModel]):
    API_ENDPOINT = wholoo().search


class SeasonFile(PartialGAPIJSON[SeasonModel]):
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


class FileMixin(TMDBMixin, register=False):
    def series_file(self, series_id: str) -> Series:
        return self._get_cached_file(
            Series,
            series_id,
            lambda: Series(self.session, self.plugin, series_id),
        )

    def search_file(self, query: str) -> SearchFile:
        return self._get_cached_file(
            SearchFile,
            query,
            lambda: SearchFile(self.session, self.plugin, query),
        )

    def movie_file(self, movie_id: str) -> Movie:
        return self._get_cached_file(
            Movie,
            movie_id,
            lambda: Movie(self.session, self.plugin, movie_id),
        )

    def season_file(self, series_id: str, season_number: int) -> SeasonFile:
        return self._get_cached_file(
            SeasonFile,
            (series_id, season_number),
            lambda: SeasonFile(self.session, self.plugin, series_id, season_number),
        )

    @staticmethod
    def _content_type(show_key: str) -> str:
        return show_key.split("/", 1)[0]

    @staticmethod
    def _content_id(show_key: str) -> str:
        return show_key.split("/", 1)[1]

    def _is_movie(self, show_key: str) -> bool:
        return self._content_type(show_key) == "movie"

    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        return f"{show_key}:{season_number}"

    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.rpartition(":")
        return show_key, int(season_number)

    def _series_model(self, series_id: str) -> TVModel:
        return self.series_file(series_id).parsed()

    def _movie_model(self, movie_id: str) -> MoviesModel:
        return self.movie_file(movie_id).parsed()

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
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id is not None:
            return existing_show.tmdb_id
        if self._is_movie(show_key):
            return None
        series_id = self._content_id(show_key)
        self.series_file(series_id).download_if_outdated()
        entity = self._series_model(series_id).details.entity
        return self._tmdb_search_media(entity.name)

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        _, season_number = self._split_season_key(season_key)
        return season_number

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        _, season_number = self._split_season_key(season_key)
        series_id = self._content_id(show_key)
        for item in self._season_items(series_id, season_number):
            if str(item.id) == episode_key:
                return int(item.number)
        return None

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie(show_key):
            return [self.movie_file(self._content_id(show_key))]
        return self._append_tmdb_show_file(
            [self.series_file(self._content_id(show_key))],
            show_key,
        )

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie(show_key):
            return [self.movie_file(self._content_id(show_key))]
        _, season_number = self._split_season_key(season_key)
        return self._append_tmdb_season_file(
            [self.season_file(self._content_id(show_key), season_number)],
            season_key,
            show_key,
        )

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if self._is_movie(show_key):
            return [self.movie_file(self._content_id(show_key))]
        _, season_number = self._split_season_key(season_key)
        return self._append_tmdb_episode_file(
            [self.season_file(self._content_id(show_key), season_number)],
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie(show_key):
            return [self._season_key(show_key, 0)]
        return [
            self._season_key(show_key, season_number)
            for season_number in self._season_numbers(self._content_id(show_key))
        ]

    @override
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_number = self._split_season_key(season_key)
            if self._is_movie(show_key):
                episode_keys.append(self._content_id(show_key))
            else:
                episode_keys += [
                    str(item.id)
                    for item in self._season_items(
                        self._content_id(show_key),
                        season_number,
                    )
                ]
        return episode_keys
