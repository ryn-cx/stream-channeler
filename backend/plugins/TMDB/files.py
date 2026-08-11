# TODO: Validate
from datetime import date, datetime
from functools import cache
from http import HTTPStatus
from typing import Any, ClassVar, Literal, overload, override

from pydantic import BaseModel
from sqlmodel import Session
from tminidb import TMiniDB
from tminidb.exceptions import HTTPError
from tminidb.movie_details.models import MovieDetailsModel
from tminidb.movie_watch_providers.models import MovieWatchProvidersModel
from tminidb.search_movie.models import SearchMovieModel
from tminidb.search_multi.models import SearchMultiModel
from tminidb.search_tv.models import SearchTvModel
from tminidb.tv_episode_details.models import TvEpisodeDetailsModel
from tminidb.tv_episode_translations.models import TvEpisodeTranslationsModel
from tminidb.tv_season_details.models import TvSeasonDetailsModel
from tminidb.tv_series_details.models import TvSeriesDetailsModel
from tminidb.tv_watch_providers.models import TvWatchProvidersModel

from app.config import settings
from app.media.media_type import MediaType
from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.utils.base_plugin.files import GAPIJSON, HTMLFile
from plugins.utils.base_plugin.plugin import BasePlugin
from plugins.utils.get_around_client import get_around_client

TMDB_DOMAIN = "themoviedb.org"


# TODO: Validate
def title_page_url(media_type: str, tmdb_id: int) -> str:
    """Return the themoviedb.org page a user would visit for a title."""
    return f"https://www.{TMDB_DOMAIN}/{media_type}/{tmdb_id}?language=en-US"


_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"
_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
_STILL_BASE_URL = "https://image.tmdb.org/t/p/original"
_LOGO_BASE_URL = "https://image.tmdb.org/t/p/w92"


# TODO: Validate
@cache
def tminidb_client() -> TMiniDB:
    # TMDB is a public API, so a direct client is used rather than the get-around
    # proxy. The read access token is stored in the keyring.
    return TMiniDB(access_token=settings.TMDB_API_READ_TOKEN)


# TODO: Validate
def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


# TODO: Validate
def release_year(value: str | date | None) -> int | None:
    if isinstance(value, date):
        return value.year
    return int(value[:4]) if value else None


# TODO: Validate
def poster_image_url(path: str | None) -> str | None:
    return _image_url(_POSTER_BASE_URL, path)


# TODO: Validate
def backdrop_image_url(path: str | None) -> str | None:
    return _image_url(_BACKDROP_BASE_URL, path)


# TODO: Validate
def still_image_url(path: str | None) -> str | None:
    return _image_url(_STILL_BASE_URL, path)


# TODO: Validate
def logo_image_url(path: str | None) -> str | None:
    return _image_url(_LOGO_BASE_URL, path)


# TODO: Validate
def duration_seconds(runtime: int | None) -> int | None:
    return runtime * 60 if runtime else None


# TODO: Validate
def air_datetime(air_date: date | None) -> datetime | None:
    # A date TMDB does not have yet comes back as an empty string rather than
    # being left out, which the generated model types as a `date` but passes
    # along as it arrived.
    if not air_date:
        return None
    return tz_datetime.combine(air_date, datetime.min.time())


# TODO: Validate
class _TMDBEndpointFile[T: BaseModel](GAPIJSON[T]):
    """TMDB endpoint file."""

    API_ENDPOINT: ClassVar[Any]

    # Occurs when a user puts in a URL for a title TMDB does not have, and when a
    # season or an episode is asked for by a number the title does not run to.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return (
            isinstance(error, HTTPError) and error.status_code == HTTPStatus.NOT_FOUND
        )


# TODO: Validate
class _TMDBIdEndpointFile[T: BaseModel](_TMDBEndpointFile[T]):
    """A TMDB file the API looks up by a title's numeric id.

    A file is keyed by a string, but TMDB checks that the response it hands back
    is for the id that was asked for, and the id it read out of the response is a
    number. A string never matches one, so the id is passed as what it is.
    """

    # TODO: Validate
    @override
    def _get(self) -> T:
        return self.API_ENDPOINT.download_and_parse(int(self.unique_identifier))


# TODO: Validate
class MovieDetails(_TMDBIdEndpointFile[MovieDetailsModel]):
    """Movie details file."""

    API_ENDPOINT = tminidb_client().movie_details


# TODO: Validate
class TvSeriesDetails(_TMDBIdEndpointFile[TvSeriesDetailsModel]):
    """TV series details file."""

    API_ENDPOINT = tminidb_client().tv_series_details


# TODO: Validate
class MovieWatchProviders(_TMDBIdEndpointFile[MovieWatchProvidersModel]):
    """Movie watch providers file."""

    API_ENDPOINT = tminidb_client().movie_watch_providers


# TODO: Validate
class TvWatchProviders(_TMDBIdEndpointFile[TvWatchProvidersModel]):
    """TV watch providers file."""

    API_ENDPOINT = tminidb_client().tv_watch_providers


# TODO: Validate
class ShowDetail(_TMDBIdEndpointFile[TvSeriesDetailsModel]):
    """Show detail file.

    The seasons and episodes under a title are reached through
    `_season_keys_from_file` and `_episode_keys_from_file`, so this file only
    carries the title itself.
    """

    API_ENDPOINT = tminidb_client().tv_series_details


# TODO: Validate
class SeasonDetail(_TMDBEndpointFile[TvSeasonDetailsModel]):
    """Season detail file."""

    API_ENDPOINT = tminidb_client().tv_season_details

    # TODO: Validate
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

    # TODO: Validate
    @override
    def _get(self) -> TvSeasonDetailsModel:
        return self.API_ENDPOINT.download_and_parse(
            self.tmdb_show_id,
            self.season_number,
        )


# TODO: Validate
class EpisodeDetail(_TMDBEndpointFile[TvEpisodeDetailsModel]):
    """Episode detail file."""

    API_ENDPOINT = tminidb_client().tv_episode_details

    # TODO: Validate
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

    # TODO: Validate
    @override
    def _get(self) -> TvEpisodeDetailsModel:
        return self.API_ENDPOINT.download_and_parse(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


# TODO: Validate
class EpisodeTranslations(_TMDBEndpointFile[TvEpisodeTranslationsModel]):
    """Every language's name for a single episode."""

    API_ENDPOINT = tminidb_client().tv_episode_translations

    # TODO: Validate
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

    # TODO: Validate
    @override
    def _get(self) -> TvEpisodeTranslationsModel:
        return self.API_ENDPOINT.download_and_parse(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


# TODO: Validate
class MultiSearch(_TMDBEndpointFile[SearchMultiModel]):
    """Multi search file."""

    API_ENDPOINT = tminidb_client().search_multi

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        page: int = 1,
    ) -> None:
        self.query = query
        self.page = page
        super().__init__(session, plugin, query if page == 1 else f"{query}/{page}")

    # TODO: Validate
    @override
    def _get(self) -> SearchMultiModel:
        return self.API_ENDPOINT.download_and_parse(self.query, page=self.page)


# TODO: Validate
class TitlePage(HTMLFile):
    """The themoviedb.org web page for a single title.

    The API this plugin otherwise uses does not carry a JustWatch link, so the
    page a user would visit is downloaded to read it off instead.
    """

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        media_type: str,
        tmdb_id: int,
    ) -> None:
        self.media_type = media_type
        self.tmdb_id = tmdb_id
        super().__init__(session, plugin, f"{media_type}/{tmdb_id}")

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            url = title_page_url(self.media_type, self.tmdb_id)
            response = get_around_client().get(url, follow_redirects=True)
            if response.status_code == HTTPStatus.NOT_FOUND:
                self.write(None)
                return
            response.raise_for_status()
            self.write(response.text)


# TODO: Validate
class MovieSearch(_TMDBEndpointFile[SearchMovieModel]):
    """Movie search file."""

    API_ENDPOINT = tminidb_client().search_movie

    # TODO: Validate
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

    # TODO: Validate
    @override
    def _get(self) -> SearchMovieModel:
        year = None if self.year is None else str(self.year)
        return self.API_ENDPOINT.download_and_parse(self.query, year=year)


# TODO: Validate
class TvSearch(_TMDBEndpointFile[SearchTvModel]):
    """TV search file."""

    API_ENDPOINT = tminidb_client().search_tv

    # TODO: Validate
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

    # TODO: Validate
    @override
    def _get(self) -> SearchTvModel:
        return self.API_ENDPOINT.download_and_parse(self.query, year=self.year)


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    # TODO: Validate
    def multi_search_file(self, query: str, page: int = 1) -> MultiSearch:
        """Returns MultiSearch file."""
        return self._file(MultiSearch, query, page)

    # TODO: Validate
    def title_page_file(self, media_type: str, tmdb_id: int) -> TitlePage:
        """Returns TitlePage file."""
        return self._file(TitlePage, media_type, tmdb_id)

    # TODO: Validate
    def movie_search_file(self, query: str, year: int | None = None) -> MovieSearch:
        """Returns MovieSearch file."""
        return self._file(MovieSearch, query, year)

    # TODO: Validate
    def tv_search_file(self, query: str, year: int | None = None) -> TvSearch:
        """Returns TvSearch file."""
        return self._file(TvSearch, query, year)

    # TODO: Validate
    def movie_detail_file(self, tmdb_id: int) -> MovieDetails:
        """Returns MovieDetails file."""
        return self._file(MovieDetails, str(tmdb_id))

    # TODO: Validate
    def show_detail_file(self, tmdb_id: int) -> ShowDetail:
        """Returns ShowDetail file."""
        return self._file(ShowDetail, tmdb_id)

    # TODO: Validate
    def season_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
    ) -> SeasonDetail:
        """Returns SeasonDetail file."""
        return self._file(SeasonDetail, tmdb_show_id, season_number)

    # TODO: Validate
    def episode_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> EpisodeDetail:
        """Returns EpisodeDetail file."""
        return self._file(
            EpisodeDetail,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    # TODO: Validate
    def episode_translations_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> EpisodeTranslations:
        """Returns EpisodeTranslations file."""
        return self._file(
            EpisodeTranslations,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    # TODO: Validate
    def tv_detail_file(self, tmdb_id: int) -> TvSeriesDetails:
        """Returns TvSeriesDetails file."""
        return self._file(TvSeriesDetails, str(tmdb_id))

    # TODO: Validate
    def movie_watch_providers_file(self, tmdb_id: int) -> MovieWatchProviders:
        """Returns MovieWatchProviders file."""
        return self._file(MovieWatchProviders, str(tmdb_id))

    # TODO: Validate
    def tv_watch_providers_file(self, tmdb_id: int) -> TvWatchProviders:
        """Returns TvWatchProviders file."""
        return self._file(TvWatchProviders, str(tmdb_id))

    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: Literal[MediaType.movie],
        tmdb_id: int,
    ) -> MovieDetails: ...
    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: Literal[MediaType.tv],
        tmdb_id: int,
    ) -> TvSeriesDetails: ...
    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieDetails | TvSeriesDetails: ...
    # TODO: Validate
    def media_detail_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieDetails | TvSeriesDetails:
        """Returns MovieDetails or TvSeriesDetails file."""
        if media_type == MediaType.movie:
            return self.movie_detail_file(tmdb_id)
        return self.tv_detail_file(tmdb_id)

    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: Literal[MediaType.movie],
        tmdb_id: int,
    ) -> MovieWatchProviders: ...
    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: Literal[MediaType.tv],
        tmdb_id: int,
    ) -> TvWatchProviders: ...
    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders: ...
    # TODO: Validate
    def watch_providers_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders:
        """Returns MovieWatchProviders or TvWatchProviders file."""
        if media_type == MediaType.movie:
            return self.movie_watch_providers_file(tmdb_id)
        return self.tv_watch_providers_file(tmdb_id)
