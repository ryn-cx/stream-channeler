# TODO: Validate
from datetime import date, datetime
from functools import cache
from typing import Any, ClassVar, Literal, overload, override

from pydantic import BaseModel
from sqlmodel import Session
from tminidb import TMiniDB
from tminidb.movie_details.models import MovieDetailsModel
from tminidb.movie_watch_providers.models import MovieWatchProvidersModel
from tminidb.search_movie.models import SearchMovieModel
from tminidb.search_multi.models import SearchMultiModel
from tminidb.search_tv.models import SearchTvModel
from tminidb.tv_episode_details.models import TvEpisodeDetailsModel
from tminidb.tv_season_details.models import TvSeasonDetailsModel
from tminidb.tv_series_details.models import TvSeriesDetailsModel
from tminidb.tv_watch_providers.models import TvWatchProvidersModel

from app.config import settings
from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.utils.base_plugin.files import GAPIJSON
from plugins.utils.base_plugin.plugin import BasePlugin

LOOKUP_ONLY_MESSAGE = (
    "TMDB is a lookup-only plugin and does not support importing or updating media."
)

_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"
_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
_STILL_BASE_URL = "https://image.tmdb.org/t/p/w300"
_LOGO_BASE_URL = "https://image.tmdb.org/t/p/w92"


@cache
def tminidb_client() -> TMiniDB:
    # TMDB is a public API, so a direct client is used rather than the get-around
    # proxy. The read access token is stored in the keyring.
    return TMiniDB(access_token=settings.TMDB_API_READ_TOKEN)


def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


def release_year(value: str | date | None) -> int | None:
    if isinstance(value, date):
        return value.year
    return int(value[:4]) if value else None


def poster_image_url(path: str | None) -> str | None:
    return _image_url(_POSTER_BASE_URL, path)


def backdrop_image_url(path: str | None) -> str | None:
    return _image_url(_BACKDROP_BASE_URL, path)


def still_image_url(path: str | None) -> str | None:
    return _image_url(_STILL_BASE_URL, path)


def logo_image_url(path: str | None) -> str | None:
    return _image_url(_LOGO_BASE_URL, path)


def duration_seconds(runtime: int | None) -> int | None:
    return runtime * 60 if runtime else None


def air_datetime(air_date: date | None) -> datetime | None:
    if air_date is None:
        return None
    return tz_datetime.combine(air_date, datetime.min.time())


class _TMDBEndpointFile[T: BaseModel](GAPIJSON[T]):
    """TMDB endpoint file."""
    API_ENDPOINT: ClassVar[Any]


class MovieDetails(_TMDBEndpointFile[MovieDetailsModel]):
    """Movie details file."""
    API_ENDPOINT = tminidb_client().movie_details


class TvSeriesDetails(_TMDBEndpointFile[TvSeriesDetailsModel]):
    """TV series details file."""
    API_ENDPOINT = tminidb_client().tv_series_details


class MovieWatchProviders(_TMDBEndpointFile[MovieWatchProvidersModel]):
    """Movie watch providers file."""
    API_ENDPOINT = tminidb_client().movie_watch_providers


class TvWatchProviders(_TMDBEndpointFile[TvWatchProvidersModel]):
    """TV watch providers file."""
    API_ENDPOINT = tminidb_client().tv_watch_providers


class ShowDetail(_TMDBEndpointFile[TvSeriesDetailsModel]):
    """Show detail file."""
    API_ENDPOINT = tminidb_client().tv_series_details

    def __init__(self, session: Session, plugin: Plugin, tmdb_id: int) -> None:
        super().__init__(session, plugin, str(tmdb_id))


class SeasonDetail(_TMDBEndpointFile[TvSeasonDetailsModel]):
    """Season detail file."""
    API_ENDPOINT = tminidb_client().tv_season_details

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{tmdb_show_id}/{season_number}")

    @override
    def _get(self) -> TvSeasonDetailsModel:
        return self.API_ENDPOINT.download_and_parse(
            self.tmdb_show_id,
            self.season_number,
        )


class EpisodeDetail(_TMDBEndpointFile[TvEpisodeDetailsModel]):
    """Episode detail file."""
    API_ENDPOINT = tminidb_client().tv_episode_details

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        self.episode_number = episode_number
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{season_number}/{episode_number}",
        )

    @override
    def _get(self) -> TvEpisodeDetailsModel:
        return self.API_ENDPOINT.download_and_parse(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


class MultiSearch(_TMDBEndpointFile[SearchMultiModel]):
    """Multi search file."""
    API_ENDPOINT = tminidb_client().search_multi

    def __init__(self, session: Session, plugin: Plugin, query: str) -> None:
        self.query = query
        super().__init__(session, plugin, query)

    @override
    def _get(self) -> SearchMultiModel:
        return self.API_ENDPOINT.download_and_parse(self.query)


class MovieSearch(_TMDBEndpointFile[SearchMovieModel]):
    """Movie search file."""
    API_ENDPOINT = tminidb_client().search_movie

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        year: int | None = None,
    ) -> None:
        self.query = query
        self.year = year
        super().__init__(session, plugin, query if year is None else f"{query}/{year}")

    @override
    def _get(self) -> SearchMovieModel:
        year = None if self.year is None else str(self.year)
        return self.API_ENDPOINT.download_and_parse(self.query, year=year)


class TvSearch(_TMDBEndpointFile[SearchTvModel]):
    """TV search file."""
    API_ENDPOINT = tminidb_client().search_tv

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        year: int | None = None,
    ) -> None:
        self.query = query
        self.year = year
        super().__init__(session, plugin, query if year is None else f"{query}/{year}")

    @override
    def _get(self) -> SearchTvModel:
        return self.API_ENDPOINT.download_and_parse(self.query, year=self.year)


class FileMixin(BasePlugin, register=False):
    def multi_search_file(self, query: str) -> MultiSearch:
        """Returns MultiSearch file."""
        return self._get_cached_file(
            MultiSearch,
            query,
            lambda: MultiSearch(self.session, self.plugin, query),
        )

    def movie_search_file(self, query: str, year: int | None = None) -> MovieSearch:
        """Returns MovieSearch file."""
        return self._get_cached_file(
            MovieSearch,
            (query, year),
            lambda: MovieSearch(self.session, self.plugin, query, year),
        )

    def tv_search_file(self, query: str, year: int | None = None) -> TvSearch:
        """Returns TvSearch file."""
        return self._get_cached_file(
            TvSearch,
            (query, year),
            lambda: TvSearch(self.session, self.plugin, query, year),
        )

    def movie_detail_file(self, tmdb_id: int) -> MovieDetails:
        """Returns MovieDetails file."""
        return self._get_cached_file(
            MovieDetails,
            tmdb_id,
            lambda: MovieDetails(self.session, self.plugin, str(tmdb_id)),
        )

    def show_detail_file(self, tmdb_id: int) -> ShowDetail:
        """Returns ShowDetail file."""
        return self._get_cached_file(
            ShowDetail,
            tmdb_id,
            lambda: ShowDetail(self.session, self.plugin, tmdb_id),
        )

    def season_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
    ) -> SeasonDetail:
        """Returns SeasonDetail file."""
        return self._get_cached_file(
            SeasonDetail,
            (tmdb_show_id, season_number),
            lambda: SeasonDetail(
                self.session,
                self.plugin,
                tmdb_show_id,
                season_number,
            ),
        )

    def episode_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> EpisodeDetail:
        """Returns EpisodeDetail file."""
        return self._get_cached_file(
            EpisodeDetail,
            (tmdb_show_id, season_number, episode_number),
            lambda: EpisodeDetail(
                self.session,
                self.plugin,
                tmdb_show_id,
                season_number,
                episode_number,
            ),
        )

    def tv_detail_file(self, tmdb_id: int) -> TvSeriesDetails:
        """Returns TvSeriesDetails file."""
        return self._get_cached_file(
            TvSeriesDetails,
            tmdb_id,
            lambda: TvSeriesDetails(self.session, self.plugin, str(tmdb_id)),
        )

    def movie_watch_providers_file(self, tmdb_id: int) -> MovieWatchProviders:
        """Returns MovieWatchProviders file."""
        return self._get_cached_file(
            MovieWatchProviders,
            tmdb_id,
            lambda: MovieWatchProviders(self.session, self.plugin, str(tmdb_id)),
        )

    def tv_watch_providers_file(self, tmdb_id: int) -> TvWatchProviders:
        """Returns TvWatchProviders file."""
        return self._get_cached_file(
            TvWatchProviders,
            tmdb_id,
            lambda: TvWatchProviders(self.session, self.plugin, str(tmdb_id)),
        )

    @overload
    def media_detail_file(
        self,
        media_type: Literal["movie"],
        tmdb_id: int,
    ) -> MovieDetails: ...
    @overload
    def media_detail_file(
        self,
        media_type: Literal["tv"],
        tmdb_id: int,
    ) -> TvSeriesDetails: ...
    def media_detail_file(
        self,
        media_type: Literal["movie", "tv"],
        tmdb_id: int,
    ) -> MovieDetails | TvSeriesDetails:
        """Returns MovieDetails or TvSeriesDetails file."""
        if media_type == "movie":
            return self.movie_detail_file(tmdb_id)
        return self.tv_detail_file(tmdb_id)

    @overload
    def watch_providers_file(
        self,
        media_type: Literal["movie"],
        tmdb_id: int,
    ) -> MovieWatchProviders: ...
    @overload
    def watch_providers_file(
        self,
        media_type: Literal["tv"],
        tmdb_id: int,
    ) -> TvWatchProviders: ...
    def watch_providers_file(
        self,
        media_type: Literal["movie", "tv"],
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders:
        """Returns MovieWatchProviders or TvWatchProviders file."""
        if media_type == "movie":
            return self.movie_watch_providers_file(tmdb_id)
        return self.tv_watch_providers_file(tmdb_id)
