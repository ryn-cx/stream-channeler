# TODO: Validate
from abc import ABC
from datetime import date, datetime, timedelta
from functools import cache
from typing import (
    override,
)

from sqlmodel import Session
from tminidb import TMiniDB
from tminidb.exceptions import ResourceNotFoundError, SeasonChangesNotFoundError
from tminidb.movie.details import MovieDetails as MovieEndpoint
from tminidb.movie.details.models import MovieDetailsModel
from tminidb.movie.translations import (
    MovieTranslations as MovieTranslationsEndpoint,
)
from tminidb.movie.translations.models import MovieTranslationsModel
from tminidb.movie.watch_providers import (
    MovieWatchProviders as MovieWatchProvidersEndpoint,
)
from tminidb.movie.watch_providers.models import MovieWatchProvidersModel
from tminidb.search.movie import SearchMovie as SearchMovieEndpoint
from tminidb.search.movie.models import SearchMovieModel
from tminidb.search.multi import SearchMulti as SearchMultiEndpoint
from tminidb.search.multi.models import SearchMultiModel
from tminidb.search.tv import SearchTv as SearchTvEndpoint
from tminidb.search.tv.models import SearchTvModel
from tminidb.tv_episode.details import TvEpisodeDetails as TvEpisodeEndpoint
from tminidb.tv_episode.details.models import TvEpisodeDetailsModel
from tminidb.tv_episode.translations import (
    TvEpisodeTranslations as TvEpisodeTranslationsEndpoint,
)
from tminidb.tv_episode.translations.models import TvEpisodeTranslationsModel
from tminidb.tv_episode_group.details import (
    TvEpisodeGroupDetails as TvEpisodeGroupEndpoint,
)
from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel
from tminidb.tv_season.changes import TvSeasonChanges as TvSeasonChangesEndpoint
from tminidb.tv_season.changes.models import TvSeasonChangesModel
from tminidb.tv_season.details import TvSeasonDetails as TvSeasonEndpoint
from tminidb.tv_season.details.models import TvSeasonDetailsModel
from tminidb.tv_season.watch_providers import (
    TvSeasonWatchProviders as TvSeasonWatchProvidersEndpoint,
)
from tminidb.tv_season.watch_providers.models import TvSeasonWatchProvidersModel
from tminidb.tv_series.changes import TvSeriesChanges as TvSeriesChangesEndpoint
from tminidb.tv_series.changes.models import TvSeriesChangesModel
from tminidb.tv_series.details import TvSeriesDetails as TvSeriesEndpoint
from tminidb.tv_series.details.models import TvSeriesDetailsModel
from tminidb.tv_series.episode_groups import (
    TvSeriesEpisodeGroups as TvSeriesEpisodeGroupsEndpoint,
)
from tminidb.tv_series.episode_groups.models import TvSeriesEpisodeGroupsModel
from tminidb.tv_series.images import TvSeriesImages as TvSeriesImagesEndpoint
from tminidb.tv_series.images.models import TvSeriesImagesModel
from tminidb.tv_series.watch_providers import (
    TvSeriesWatchProviders as TvSeriesWatchProvidersEndpoint,
)
from tminidb.tv_series.watch_providers.models import TvSeriesWatchProvidersModel

from app.config import settings
from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.utils.base_plugin_v3.files import (
    EndpointFile,
    IntegerEndpointFile,
)


@cache
def tminidb() -> TMiniDB:
    return TMiniDB(settings.TMDB_API_READ_TOKEN)


class MoviesDetails(IntegerEndpointFile[MovieDetailsModel]):
    custom_class_key = "Movies/Details"

    @override
    def _endpoint(self) -> MovieEndpoint:
        return tminidb().movie.details

    # Occurs if the user tries to add an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class MoviesTranslations(IntegerEndpointFile[MovieTranslationsModel]):
    custom_class_key = "Movies/Translations"

    @override
    def _endpoint(self) -> MovieTranslationsEndpoint:
        return tminidb().movie.translations


# TODO: Validate
class WatchProvidersFile[T](EndpointFile[T], ABC):
    # TODO: Validate
    @override
    def _downloaded_status(self) -> str:
        return "Incomplete"


class MoviesWatchProviders(WatchProvidersFile[MovieWatchProvidersModel]):
    custom_class_key = "Movies/Watch Providers"

    @override
    def _endpoint(self) -> MovieWatchProvidersEndpoint:
        return tminidb().movie.watch_providers

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_movie_id: int,
        downloaded_at: date,
    ) -> None:
        self.tmdb_movie_id = tmdb_movie_id
        super().__init__(
            session=session,
            plugin=plugin,
            unique_identifier=f"{tmdb_movie_id}/{downloaded_at.isoformat()}",
        )

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_movie_id)


class TVSeriesWatchProviders(WatchProvidersFile[TvSeriesWatchProvidersModel]):
    custom_class_key = "TV Series/Watch Providers"

    @override
    def _endpoint(self) -> TvSeriesWatchProvidersEndpoint:
        return tminidb().tv_series.watch_providers

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        downloaded_at: date,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        super().__init__(
            session=session,
            plugin=plugin,
            unique_identifier=f"{tmdb_show_id}/{downloaded_at.isoformat()}",
        )

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_show_id)


class TVSeasonsWatchProviders(WatchProvidersFile[TvSeasonWatchProvidersModel]):
    custom_class_key = "TV Seasons/Watch Providers"

    @override
    def _endpoint(self) -> TvSeasonWatchProvidersEndpoint:
        return tminidb().tv_season.watch_providers

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
        downloaded_at: date,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{season_number}/{downloaded_at.isoformat()}",
        )

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_show_id, self.season_number)


type ProvidersFile = (
    MoviesWatchProviders | TVSeriesWatchProviders | TVSeasonsWatchProviders
)


class TVSeriesDetails(IntegerEndpointFile[TvSeriesDetailsModel]):
    custom_class_key = "TV Series/Details"

    @override
    def _endpoint(self) -> TvSeriesEndpoint:
        return tminidb().tv_series.details

    # Occurs if the user tries to add an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class TVSeriesImages(IntegerEndpointFile[TvSeriesImagesModel]):
    custom_class_key = "TV Series/Images"

    @override
    def _endpoint(self) -> TvSeriesImagesEndpoint:
        return tminidb().tv_series.images

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            series_id=int(self.unique_identifier),
            include_image_language="en,null",
        )


class TVSeriesEpisodeGroups(IntegerEndpointFile[TvSeriesEpisodeGroupsModel]):
    custom_class_key = "TV Series/Episode Groups"

    @override
    def _endpoint(self) -> TvSeriesEpisodeGroupsEndpoint:
        return tminidb().tv_series.episode_groups


class TVEpisodeGroupsDetails(EndpointFile[TvEpisodeGroupDetailsModel]):
    custom_class_key = "TV Episode Groups/Details"

    @override
    def _endpoint(self) -> TvEpisodeGroupEndpoint:
        return tminidb().tv_episode_group.details


class TVSeasonsDetails(EndpointFile[TvSeasonDetailsModel]):
    custom_class_key = "TV Seasons/Details"

    @override
    def _endpoint(self) -> TvSeasonEndpoint:
        return tminidb().tv_season.details

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

    # Occurs if the user tries to add an invalid URL.
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_show_id, self.season_number)

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class TVEpisodesDetails(EndpointFile[TvEpisodeDetailsModel]):
    custom_class_key = "TV Episodes/Details"

    @override
    def _endpoint(self) -> TvEpisodeEndpoint:
        return tminidb().tv_episode.details

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
            session=session,
            plugin=plugin,
            unique_identifier=f"{tmdb_show_id}/{season_number}/{episode_number}",
        )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            series_id=self.tmdb_show_id,
            season_number=self.season_number,
            episode_number=self.episode_number,
        )


class TVEpisodesTranslations(EndpointFile[TvEpisodeTranslationsModel]):
    custom_class_key = "TV Episodes/Translations"

    @override
    def _endpoint(self) -> TvEpisodeTranslationsEndpoint:
        return tminidb().tv_episode.translations

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
            session=session,
            plugin=plugin,
            unique_identifier=f"{tmdb_show_id}/{season_number}/{episode_number}",
        )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            series_id=self.tmdb_show_id,
            season_number=self.season_number,
            episode_number=self.episode_number,
        )


class TVSeriesChanges(EndpointFile[TvSeriesChangesModel]):
    custom_class_key = "TV Series/Changes"

    @override
    def _endpoint(self) -> TvSeriesChangesEndpoint:
        return tminidb().tv_series.changes

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        since: date,
        downloaded_to: date,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.since = since
        super().__init__(
            session=session,
            plugin=plugin,
            unique_identifier=f"{tmdb_show_id}/{downloaded_to.isoformat()}",
        )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download_merged(
            series_id=self.tmdb_show_id,
            start_date=self.since,
            end_date=tz_datetime.now().date(),
        )


class TVSeasonsChanges(EndpointFile[TvSeasonChangesModel]):
    custom_class_key = "TV Seasons/Changes"

    @override
    def _endpoint(self) -> TvSeasonChangesEndpoint:
        return tminidb().tv_season.changes

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        season_tmdb_id: int,
        changed_on: date,
    ) -> None:
        self.season_tmdb_id = season_tmdb_id
        self.changed_on = changed_on
        super().__init__(
            session=session,
            plugin=plugin,
            unique_identifier=f"{season_tmdb_id}/{changed_on.isoformat()}",
        )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            season_id=self.season_tmdb_id,
            start_date=self.changed_on,
            end_date=self.changed_on,
        )

    @override
    def _next_update_at(self) -> datetime | None:
        # A day that is not over can still take more changes, so the file asks to
        # be read again once it is. A day already over takes no more.
        if self.changed_on < tz_datetime.now().date():
            return None
        return tz_datetime.combine(
            self.changed_on + timedelta(days=1),
            datetime.min.time(),
        )

    # Occurs when TMDB keeps no change log for the season.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeasonChangesNotFoundError)


class SearchMulti(EndpointFile[SearchMultiModel]):
    custom_class_key = "Search/Multi"

    @override
    def _endpoint(self) -> SearchMultiEndpoint:
        return tminidb().search.multi

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        page: int = 1,
    ) -> None:
        self.query = query
        self.page = page
        super().__init__(session, plugin, f"{query}/{page}")

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, page=self.page)

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


class SearchMovie(EndpointFile[SearchMovieModel]):
    custom_class_key = "Search/Movie"

    @override
    def _endpoint(self) -> SearchMovieEndpoint:
        return tminidb().search.movie

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
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, year=self.year)

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


class SearchTV(EndpointFile[SearchTvModel]):
    custom_class_key = "Search/TV"

    @override
    def _endpoint(self) -> SearchTvEndpoint:
        return tminidb().search.tv

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
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, year=self.year)

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)
