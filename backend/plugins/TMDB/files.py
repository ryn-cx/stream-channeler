# TODO: Validate
from collections.abc import Generator, Sequence
from datetime import date, datetime
from functools import cache
from http import HTTPStatus
from typing import Any, ClassVar, Literal, overload, override

from pydantic import BaseModel
from sqlmodel import Session, col, or_, select
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
from app.files.models import File
from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, HTMLFile, JSONFile
from plugins.utils.base_plugin.plugin import BasePlugin
from plugins.utils.get_around_client import get_around_client

TMDB_DOMAIN = "themoviedb.org"


def title_page_url(media_type: str, tmdb_id: int) -> str:
    """Return the themoviedb.org page a user would visit for a title."""
    return f"https://www.{TMDB_DOMAIN}/{media_type}/{tmdb_id}?language=en-US"


_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"
_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
_STILL_BASE_URL = "https://image.tmdb.org/t/p/original"
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
    # A date TMDB does not have yet comes back as an empty string rather than
    # being left out, which the generated model types as a `date` but passes
    # along as it arrived.
    if not air_date:
        return None
    return tz_datetime.combine(air_date, datetime.min.time())


class _TMDBEndpointFile[T: BaseModel](GAPIJSON[T]):
    """TMDB endpoint file."""

    API_ENDPOINT: ClassVar[Any]


class _TMDBIdEndpointFile[T: BaseModel](_TMDBEndpointFile[T]):
    """A TMDB file the API looks up by a title's numeric id.

    A file is keyed by a string, but TMDB checks that the response it hands back
    is for the id that was asked for, and the id it read out of the response is a
    number. A string never matches one, so the id is passed as what it is.
    """

    @override
    def _get(self) -> T:
        return self.API_ENDPOINT.download_and_parse(int(self.unique_identifier))


class MovieDetails(_TMDBIdEndpointFile[MovieDetailsModel]):
    """Movie details file."""

    API_ENDPOINT = tminidb_client().movie_details


class TvSeriesDetails(_TMDBIdEndpointFile[TvSeriesDetailsModel]):
    """TV series details file."""

    API_ENDPOINT = tminidb_client().tv_series_details


class MovieWatchProviders(_TMDBIdEndpointFile[MovieWatchProvidersModel]):
    """Movie watch providers file."""

    API_ENDPOINT = tminidb_client().movie_watch_providers


class TvWatchProviders(_TMDBIdEndpointFile[TvWatchProvidersModel]):
    """TV watch providers file."""

    API_ENDPOINT = tminidb_client().tv_watch_providers


class ShowDetail(_TMDBIdEndpointFile[TvSeriesDetailsModel]):
    """Show detail file."""

    API_ENDPOINT = tminidb_client().tv_series_details

    def __init__(self, session: Session, plugin: Plugin, tmdb_id: int) -> None:
        self.session = session
        self.plugin = plugin
        self.tmdb_id = tmdb_id
        self._children_are_stored = False
        self._child_records: Sequence[File] = []
        super().__init__(session, plugin, str(tmdb_id))

    def _preload_child_records(self) -> None:
        """Load every child's record in one query.

        Each child is looked up by key, which is a query each unless the record is
        already in the session.
        """
        statement = select(File).where(
            File.plugin_id == self.plugin.id,
            or_(
                col(File.key).startswith(f"{SeasonDetail.__name__}/{self.tmdb_id}/"),
                col(File.key).startswith(f"{EpisodeDetail.__name__}/{self.tmdb_id}/"),
                col(File.key).startswith(
                    f"{EpisodeTranslations.__name__}/{self.tmdb_id}/",
                ),
            ),
        )
        # The session only holds records weakly, so they have to be kept alive for
        # the lookups to find them.
        self._child_records = self.session.exec(statement).all()

    def _child_files(self) -> Generator[BaseFile[Any]]:
        self._preload_child_records()
        for season in self.parsed().seasons:
            season_file = SeasonDetail(
                self.session,
                self.plugin,
                self.tmdb_id,
                season.season_number,
            )
            yield season_file
            if season_file.is_outdated():
                continue
            for episode in season_file.parsed().episodes:
                yield EpisodeDetail(
                    self.session,
                    self.plugin,
                    self.tmdb_id,
                    season.season_number,
                    episode.episode_number,
                )
                yield EpisodeTranslations(
                    self.session,
                    self.plugin,
                    self.tmdb_id,
                    season.season_number,
                    episode.episode_number,
                )

    @override
    def _download(self) -> None:
        super()._download()
        for child_file in self._child_files():
            child_file.download_if_outdated()

    @override
    def is_outdated(self, minimum_timestamp: datetime | None = None) -> bool:
        if super().is_outdated(minimum_timestamp):
            return True
        # Walking the children is expensive and they are only ever added by
        # `_download`, so once they are all stored the walk cannot find anything.
        if self._children_are_stored:
            return False
        self._children_are_stored = not any(
            child_file.is_outdated() for child_file in self._child_files()
        )
        return not self._children_are_stored


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


class EpisodeTranslationData(BaseModel):
    """The translated fields of a single translation."""

    name: str | None = None
    overview: str | None = None


class EpisodeTranslation(BaseModel):
    """One language's version of an episode."""

    iso_639_1: str | None = None
    iso_3166_1: str | None = None
    data: EpisodeTranslationData


class EpisodeTranslations(JSONFile[list[EpisodeTranslation]]):
    """Every language's name for a single episode."""

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
        self.unique_identifier = f"{tmdb_show_id}/{season_number}/{episode_number}"
        super().__init__(session, plugin)

    @override
    def _parse(self, raw: Any) -> list[EpisodeTranslation]:
        return [
            EpisodeTranslation.model_validate(translation)
            for translation in raw["translations"]
        ]

    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            endpoint = (
                f"tv/{self.tmdb_show_id}/season/{self.season_number}"
                f"/episode/{self.episode_number}/translations"
            )
            content = tminidb_client().download(endpoint, {}, log_id=self.file_key())
            self.write(content)


class MultiSearch(_TMDBEndpointFile[SearchMultiModel]):
    """Multi search file."""

    API_ENDPOINT = tminidb_client().search_multi

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

    @override
    def _get(self) -> SearchMultiModel:
        return self.API_ENDPOINT.download_and_parse(self.query, page=self.page)


class TitlePage(HTMLFile):
    """The themoviedb.org web page for a single title.

    The API this plugin otherwise uses does not carry a JustWatch link, so the
    page a user would visit is downloaded to read it off instead.
    """

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
    def multi_search_file(self, query: str, page: int = 1) -> MultiSearch:
        """Returns MultiSearch file."""
        return self._file(MultiSearch, query, page)

    def title_page_file(self, media_type: str, tmdb_id: int) -> TitlePage:
        """Returns TitlePage file."""
        return self._file(TitlePage, media_type, tmdb_id)

    def movie_search_file(self, query: str, year: int | None = None) -> MovieSearch:
        """Returns MovieSearch file."""
        return self._file(MovieSearch, query, year)

    def tv_search_file(self, query: str, year: int | None = None) -> TvSearch:
        """Returns TvSearch file."""
        return self._file(TvSearch, query, year)

    def movie_detail_file(self, tmdb_id: int) -> MovieDetails:
        """Returns MovieDetails file."""
        return self._file(MovieDetails, str(tmdb_id))

    def show_detail_file(self, tmdb_id: int) -> ShowDetail:
        """Returns ShowDetail file."""
        return self._file(ShowDetail, tmdb_id)

    def season_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
    ) -> SeasonDetail:
        """Returns SeasonDetail file."""
        return self._file(SeasonDetail, tmdb_show_id, season_number)

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

    def tv_detail_file(self, tmdb_id: int) -> TvSeriesDetails:
        """Returns TvSeriesDetails file."""
        return self._file(TvSeriesDetails, str(tmdb_id))

    def movie_watch_providers_file(self, tmdb_id: int) -> MovieWatchProviders:
        """Returns MovieWatchProviders file."""
        return self._file(MovieWatchProviders, str(tmdb_id))

    def tv_watch_providers_file(self, tmdb_id: int) -> TvWatchProviders:
        """Returns TvWatchProviders file."""
        return self._file(TvWatchProviders, str(tmdb_id))

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
