# TODO: Validate
from functools import cache
from typing import (
    override,
)

from sqlmodel import Session
from tminidb import TMiniDB
from tminidb.exceptions import ResourceNotFoundError
from tminidb.movie.details import MovieDetails as MovieEndpoint
from tminidb.movie.details.models import MovieDetailsModel
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
from tminidb.tv_episode_group.details import (
    TvEpisodeGroupDetails as TvEpisodeGroupEndpoint,
)
from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel
from tminidb.tv_season.details import TvSeasonDetails as TvSeasonEndpoint
from tminidb.tv_season.details.models import TvSeasonDetailsModel
from tminidb.tv_season.watch_providers import (
    TvSeasonWatchProviders as TvSeasonWatchProvidersEndpoint,
)
from tminidb.tv_season.watch_providers.models import TvSeasonWatchProvidersModel
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
from plugins.utils.base_plugin.files import (
    IntegerArgEndpointFile,
    MultipleArgEndpointFile,
    SingleArgEndpointFile,
)


# TODO: Validate
@cache
def tminidb() -> TMiniDB:
    return TMiniDB(settings.TMDB_API_READ_TOKEN)


# TODO: Validate
class MoviesDetails(IntegerArgEndpointFile[MovieDetailsModel]):
    custom_class_key = "Movies/Details"

    # TODO: Validate
    @override
    def _endpoint(self) -> MovieEndpoint:
        return tminidb().movie.details

    # Occurs if the user tries to add an invalid URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class MoviesWatchProviders(IntegerArgEndpointFile[MovieWatchProvidersModel]):
    custom_class_key = "Movies/Watch Providers"

    # TODO: Validate
    @override
    def _endpoint(self) -> MovieWatchProvidersEndpoint:
        return tminidb().movie.watch_providers


# TODO: Validate
class TVSeriesWatchProviders(IntegerArgEndpointFile[TvSeriesWatchProvidersModel]):
    custom_class_key = "TV Series/Watch Providers"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesWatchProvidersEndpoint:
        return tminidb().tv_series.watch_providers


# TODO: Validate
class TVSeasonsWatchProviders(MultipleArgEndpointFile[TvSeasonWatchProvidersModel]):
    custom_class_key = "TV Seasons/Watch Providers"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeasonWatchProvidersEndpoint:
        return tminidb().tv_season.watch_providers

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> None:
        self.tmdb_tv_title_id = tmdb_tv_title_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{tmdb_tv_title_id}/{season_number}")

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_tv_title_id, self.season_number)


# TODO: Validate
class TVSeriesDetails(IntegerArgEndpointFile[TvSeriesDetailsModel]):
    custom_class_key = "TV Series/Details"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesEndpoint:
        return tminidb().tv_series.details

    # Occurs if the user tries to add an invalid URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class TVSeriesImages(MultipleArgEndpointFile[TvSeriesImagesModel]):
    custom_class_key = "TV Series/Images"

    # TODO: Validate
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


# TODO: Validate
class TVSeriesEpisodeGroups(IntegerArgEndpointFile[TvSeriesEpisodeGroupsModel]):
    custom_class_key = "TV Series/Episode Groups"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesEpisodeGroupsEndpoint:
        return tminidb().tv_series.episode_groups


# TODO: Validate
class TVEpisodeGroupsDetails(SingleArgEndpointFile[TvEpisodeGroupDetailsModel]):
    custom_class_key = "TV Episode Groups/Details"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvEpisodeGroupEndpoint:
        return tminidb().tv_episode_group.details


# TODO: Validate
class TVSeasonsDetails(MultipleArgEndpointFile[TvSeasonDetailsModel]):
    custom_class_key = "TV Seasons/Details"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeasonEndpoint:
        return tminidb().tv_season.details

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> None:
        self.tmdb_tv_title_id = tmdb_tv_title_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{tmdb_tv_title_id}/{season_number}")

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_tv_title_id, self.season_number)


# TODO: Validate
class SearchMulti(MultipleArgEndpointFile[SearchMultiModel]):
    custom_class_key = "Search/Multi"

    # TODO: Validate
    @override
    def _endpoint(self) -> SearchMultiEndpoint:
        return tminidb().search.multi

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
        super().__init__(session, plugin, f"{query}/{page}")

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, page=self.page)


# TODO: Validate
class SearchMovie(MultipleArgEndpointFile[SearchMovieModel]):
    custom_class_key = "Search/Movie"

    # TODO: Validate
    @override
    def _endpoint(self) -> SearchMovieEndpoint:
        return tminidb().search.movie

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
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, year=self.year)


# TODO: Validate
class SearchTV(MultipleArgEndpointFile[SearchTvModel]):
    custom_class_key = "Search/TV"

    # TODO: Validate
    @override
    def _endpoint(self) -> SearchTvEndpoint:
        return tminidb().search.tv

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
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, year=self.year)
