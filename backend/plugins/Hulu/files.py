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
from wholoo.season.models import Item as SeasonItem
from wholoo.season.models import SeasonModel
from wholoo.tv import TV
from wholoo.tv.models import TVModel

from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.Hulu.identity import HuluIdentity
from plugins.Hulu.utils import HuluMediaType
from plugins.utils.abstract_plugin import TMDBLookupInfo
from plugins.utils.base_plugin_v2.base import BasePlugin
from plugins.utils.base_plugin_v2.files import BaseFile, EndpointFile
from plugins.utils.get_around_client import get_around_client


@cache
def wholoo() -> Wholoo:
    """Return a cached Wholoo client."""
    return Wholoo(get_around_client=get_around_client())


class Series(EndpointFile[TVModel]):
    @override
    def _endpoint(self) -> TV:
        return wholoo().tv

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)

    def tmdb_lookup_info(self) -> TMDBLookupInfo:
        parsed_series = self.parsed()
        return TMDBLookupInfo(
            title=parsed_series.name,
            media_type="Series",
            year=parsed_series.details.entity.premiere_date.year,
        )


class Movie(EndpointFile[MoviesModel]):
    @override
    def _endpoint(self) -> MoviesEndpoint:
        return wholoo().movies

    # Occurs if the user tries to add an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)

    def tmdb_lookup_info(self) -> TMDBLookupInfo:
        model = self.parsed()
        return TMDBLookupInfo(
            title=model.name,
            media_type="Movie",
            year=model.details.entity.premiere_date.year,
        )


class Season(EndpointFile[SeasonModel]):
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

    def season_name(self) -> str:
        return self.parsed().series_grouping_metadata.grouping_name


class Episode(EndpointFile[EpisodeModel]):
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
    def series_id(self) -> str:
        """Return the id of the series the episode belongs to."""
        return str(self.parsed().details.vod_items.focus.entity.series_id)


# TODO: Validate
class SitemapPage[T: GenresModel | GenreModel](EndpointFile[T]):
    # TODO: Validate
    def listed_items(self) -> list[tuple[str, str]]:
        layout = self.parsed().props.page_props.layout
        return [
            (item.name, item.href)
            for component in layout.components or []
            if component.type == "list_card"
            for item in component.items or []
            if item.name and item.href
        ]


# TODO: Validate
class Genres(SitemapPage[GenresModel]):
    """Genre list file."""

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin) -> None:
        """Initialize the file."""
        super().__init__(session, plugin, "genres")

    # TODO: Validate
    @override
    def _endpoint(self) -> GenresEndpoint:
        return wholoo().genres

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download()


# TODO: Validate
class Genre(SitemapPage[GenreModel]):
    """One genre's title list file."""

    # TODO: Validate
    def media_urls(self) -> list[str]:
        paths = {
            href: None
            for _name, href in self.listed_items()
            if href.startswith(
                (f"/{HuluMediaType.MOVIE}/", f"/{HuluMediaType.SERIES}/"),
            )
        }
        return [HuluIdentity.build_url(path) for path in paths]

    # TODO: Validate
    @override
    def _endpoint(self) -> GenreEndpoint:
        return wholoo().genre

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, GenreNotFoundError)


# TODO: Validate
class FileMixin(BasePlugin):
    # TODO: Validate
    def genres_page_file(self) -> Genres:
        """Return GenresPage file."""
        return self._file(Genres)

    # TODO: Validate
    def genre_page_file(self, genre_id: str) -> Genre:
        """Return GenrePage file."""
        return self._file(Genre, genre_id)

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BaseFile[Any]]:
        genres_page = self.genres_page_file()
        return [
            genres_page,
            *(
                self.genre_page_file(href.rsplit("/", 1)[-1])
                for _name, href in genres_page.listed_items()
            ),
        ]

    # TODO: Validate
    def series_file(self, series_id: str) -> Series:
        """Return Series file."""
        return self._file(Series, series_id)

    # TODO: Validate
    def episode_hub_file(self, episode_id: str) -> Episode:
        """Return EpisodeHub file."""
        return self._file(Episode, episode_id)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> Movie:
        """Return Movie file."""
        return self._file(Movie, movie_id)

    # TODO: Validate
    def season_file(self, series_id: str, season_number: int) -> Season:
        """Return SeasonFile file."""
        return self._file(Season, series_id, season_number)

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
class SeriesFileMixin(FileMixin):
    # TODO: Validate
    @override
    def get_tmdb_lookup_info(self, show_key: str) -> TMDBLookupInfo:
        return self.series_file(show_key).tmdb_lookup_info()

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.series_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the season and new episodes of it.
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
                str(item.id) for item in self._season_items(show_key, season_number)
            ]
        return episode_keys


# TODO: Validate
class MovieFileMixin(FileMixin):
    # TODO: Validate
    @override
    def get_tmdb_lookup_info(self, show_key: str) -> TMDBLookupInfo:
        return self.movie_file(show_key).tmdb_lookup_info()

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.movie_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the season and new episodes of it.
        return [self.movie_file(show_key)]

    # TODO: Validate
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
