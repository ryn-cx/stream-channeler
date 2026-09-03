# TODO: Validate
"""The files Hulu is read out of."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import cache
from http import HTTPStatus
from typing import Any, override

from sqlmodel import Session
from wholoo import Wholoo
from wholoo.episode import Episode as EpisodeEndpoint
from wholoo.episode.models import EpisodeModel
from wholoo.exceptions import (
    EpisodeNotFoundError,
    GenreNotFoundError,
    HTTPError,
    MovieNotFoundError,
    SeriesNotFoundError,
)
from wholoo.genre import Genre as GenreEndpoint
from wholoo.genre.models import GenreModel
from wholoo.genres import Genres as GenresEndpoint
from wholoo.genres.models import GenresModel
from wholoo.movies import Movies as MoviesEndpoint
from wholoo.movies.models import MoviesModel
from wholoo.search import Search as SearchEndpoint
from wholoo.search.models import SearchModel
from wholoo.season import Season as SeasonEndpoint
from wholoo.season.models import SeasonModel
from wholoo.tv import TV
from wholoo.tv.models import TVModel

from app.media.media_type import TMDBMediaType
from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.Hulu.utils import UtilsMixin, listed_items
from plugins.utils.abstract_plugin import TMDBLookupInfo
from plugins.utils.base_plugin_v2.files import BaseFile, EndpointFile
from plugins.utils.get_around_client import get_around_client


@cache
def wholoo() -> Wholoo:
    return Wholoo(get_around_client=get_around_client())


# TODO: Validate
class _Series(EndpointFile[TVModel]):
    @override
    def _endpoint(self) -> TV:
        return wholoo().tv

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


# TODO: Validate
class _Movie(EndpointFile[MoviesModel]):
    @override
    def _endpoint(self) -> MoviesEndpoint:
        return wholoo().movies

    # Occurs if the user tries to add an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)


# TODO: Validate
class _Season(EndpointFile[SeasonModel]):
    @override
    def _endpoint(self) -> SeasonEndpoint:
        return wholoo().season

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
    def _download_file(self) -> str:
        return self._endpoint().download(self.series_id, self.season_number)


# TODO: Validate
class _Episode(EndpointFile[EpisodeModel]):
    @override
    def _endpoint(self) -> EpisodeEndpoint:
        return wholoo().episode

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        if isinstance(error, EpisodeNotFoundError):
            return True
        return (
            isinstance(error, HTTPError) and error.status_code == HTTPStatus.BAD_REQUEST
        )


# TODO: Validate
class _Genres(EndpointFile[GenresModel]):
    @override
    def _endpoint(self) -> GenresEndpoint:
        return wholoo().genres

    @override
    def _download_file(self) -> str:
        return self._endpoint().download()


# TODO: Validate
class _Genre(EndpointFile[GenreModel]):
    @override
    def _endpoint(self) -> GenreEndpoint:
        return wholoo().genre


# TODO: Validate
class FileMixin(UtilsMixin):
    # TODO: Validate
    def genres_file(self) -> _Genres:
        return self._file(_Genres, "genres")

    # TODO: Validate
    def genre_page_file(self, genre_id: str) -> _Genre:
        return self._file(_Genre, genre_id)

    # TODO: Validate
    def series_file(self, series_id: str) -> _Series:
        return self._file(_Series, series_id)

    # TODO: Validate
    def episode_file(self, episode_id: str) -> _Episode:
        return self._file(_Episode, episode_id)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> _Movie:
        return self._file(_Movie, movie_id)

    # TODO: Validate
    def season_file(self, series_id: str, season_number: int) -> _Season:
        return self._file(_Season, series_id, season_number)

    # TODO: Validate
    def _season_numbers(self, series_id: str) -> list[int]:
        numbers: dict[int, None] = {}
        for component in self.series_file(series_id).parsed().components:
            for item in component.items:
                grouping = item.series_grouping_metadata
                if grouping is not None:
                    numbers[grouping.season_number] = None
        return list(numbers)

    @override
    def _source_files(self) -> Sequence[BaseFile[Any]]:
        genres_page = self.genres_file()
        return [
            genres_page,
            *(
                self.genre_page_file(href.rsplit("/", 1)[-1])
                for _name, href in listed_items(genres_page.parsed())
            ),
        ]


# TODO: Validate
class SeriesFileMixin(FileMixin):
    @override
    def tmdb_lookup_info(self, show_key: str) -> TMDBLookupInfo:
        parsed_series = self.series_file(show_key).parsed()
        return TMDBLookupInfo(
            title=parsed_series.name,
            media_type=TMDBMediaType.tv,
            year=parsed_series.details.entity.premiere_date.year,
        )

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Includes show information and the list of seasons.
        return [self.series_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, season_number = self._split_season_key(season_key)
        # Includes season information and the list of episodes.
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
        _, season_number = self._split_season_key(season_key)
        return [self.season_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            self._season_key(show_key, season_number)
            for season_number in self._season_numbers(show_key)
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_number = self._split_season_key(season_key)
            episode_keys += [
                str(item.id)
                for item in self.season_file(show_key, season_number).parsed().items
            ]
        return episode_keys


# TODO: Validate
class MovieFileMixin(FileMixin):
    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> TMDBLookupInfo:
        parsed_movie = self.movie_file(show_key).parsed()
        return TMDBLookupInfo(
            title=parsed_movie.name,
            media_type=TMDBMediaType.movie,
            year=parsed_movie.details.entity.premiere_date.year,
        )

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [self._season_key(show_key, 0)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [self._split_season_key(season_key)[0] for season_key in season_keys]
