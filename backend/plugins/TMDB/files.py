# TODO: Validate
import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import (
    ClassVar,
    override,
)

from i_am_the_db import IAmTheDB
from i_am_the_db.exceptions import TitleNotFoundError
from i_am_the_db.title import Title as IMDbTitleEndpoint
from i_am_the_db.title.models import TitleModel as IMDbTitleModel
from sqlmodel import Session
from tminidb import TMiniDB
from tminidb.changes.movie_list import ChangesMovieList as ChangesMovieListEndpoint
from tminidb.changes.movie_list.models import ChangesMovieListModel
from tminidb.changes.tv_list import ChangesTvList as ChangesTvListEndpoint
from tminidb.changes.tv_list.models import ChangesTvListModel
from tminidb.exceptions import ResourceNotFoundError
from tminidb.find.by_id import FindById as FindByIdEndpoint
from tminidb.find.by_id.models import FindByIdModel
from tminidb.movie.details import MovieDetails as MovieEndpoint
from tminidb.movie.details.models import MovieDetailsModel
from tminidb.movie.external_ids import MovieExternalIds as MovieExternalIdsEndpoint
from tminidb.movie.external_ids.models import MovieExternalIdsModel
from tminidb.movie.keywords import MovieKeywords as MovieKeywordsEndpoint
from tminidb.movie.keywords.models import MovieKeywordsModel
from tminidb.movie.recommendations import (
    MovieRecommendations as MovieRecommendationsEndpoint,
)
from tminidb.movie.recommendations.models import MovieRecommendationsModel
from tminidb.movie.similar import MovieSimilar as MovieSimilarEndpoint
from tminidb.movie.similar.models import MovieSimilarModel
from tminidb.movie.videos import MovieVideos as MovieVideosEndpoint
from tminidb.movie.videos.models import MovieVideosModel
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
from tminidb.tv_series.external_ids import (
    TvSeriesExternalIds as TvSeriesExternalIdsEndpoint,
)
from tminidb.tv_series.external_ids.models import TvSeriesExternalIdsModel
from tminidb.tv_series.images import TvSeriesImages as TvSeriesImagesEndpoint
from tminidb.tv_series.images.models import TvSeriesImagesModel
from tminidb.tv_series.keywords import (
    TvSeriesKeywords as TvSeriesKeywordsEndpoint,
)
from tminidb.tv_series.keywords.models import TvSeriesKeywordsModel
from tminidb.tv_series.recommendations import (
    TvSeriesRecommendations as TvSeriesRecommendationsEndpoint,
)
from tminidb.tv_series.recommendations.models import TvSeriesRecommendationsModel
from tminidb.tv_series.similar import TvSeriesSimilar as TvSeriesSimilarEndpoint
from tminidb.tv_series.similar.models import TvSeriesSimilarModel
from tminidb.tv_series.videos import TvSeriesVideos as TvSeriesVideosEndpoint
from tminidb.tv_series.videos.models import TvSeriesVideosModel
from tminidb.tv_series.watch_providers import (
    TvSeriesWatchProviders as TvSeriesWatchProvidersEndpoint,
)
from tminidb.tv_series.watch_providers.models import TvSeriesWatchProvidersModel

from app.config import settings
from app.media.media_type import TMDBMediaType
from app.plugins.models import Plugin
from app.tmdb_media.tmdb import tmdb_title_key
from app.utils import tz_datetime
from plugins.utils.base_plugin.files import (
    IntegerArgEndpointFile,
    MultipleArgEndpointFile,
    PagedEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.base_plugin.update_at import staggered_yearly_update_at
from plugins.utils.constants import INCOMPLETE_STATUS, ROLLING_CHANGES_UPDATE_INTERVAL
from plugins.utils.proxy_client import proxy_client


# TODO: Validate
@cache
def tminidb() -> TMiniDB:
    return TMiniDB(settings.TMDB_API_READ_TOKEN)


# TODO: Validate
@cache
def i_am_the_db() -> IAmTheDB:
    return IAmTheDB(get_around_client=proxy_client())


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
    @override
    def _next_update_at(self) -> datetime:
        return staggered_yearly_update_at(self.file_key(), tz_datetime.now())


# TODO: Validate
class MoviesRecommendations(IntegerArgEndpointFile[MovieRecommendationsModel]):
    custom_class_key = "Movies/Recommendations"

    # TODO: Validate
    @override
    def _endpoint(self) -> MovieRecommendationsEndpoint:
        return tminidb().movie.recommendations


# TODO: Validate
class TVSeriesRecommendations(IntegerArgEndpointFile[TvSeriesRecommendationsModel]):
    custom_class_key = "TV Series/Recommendations"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesRecommendationsEndpoint:
        return tminidb().tv_series.recommendations


# TODO: Validate
class MoviesKeywords(IntegerArgEndpointFile[MovieKeywordsModel]):
    custom_class_key = "Movies/Keywords"

    # TODO: Validate
    @override
    def _endpoint(self) -> MovieKeywordsEndpoint:
        return tminidb().movie.keywords


# TODO: Validate
class TVSeriesKeywords(IntegerArgEndpointFile[TvSeriesKeywordsModel]):
    custom_class_key = "TV Series/Keywords"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesKeywordsEndpoint:
        return tminidb().tv_series.keywords


# TODO: Validate
class MoviesSimilar(IntegerArgEndpointFile[MovieSimilarModel]):
    custom_class_key = "Movies/Similar"

    # TODO: Validate
    @override
    def _endpoint(self) -> MovieSimilarEndpoint:
        return tminidb().movie.similar


# TODO: Validate
class TVSeriesSimilar(IntegerArgEndpointFile[TvSeriesSimilarModel]):
    custom_class_key = "TV Series/Similar"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesSimilarEndpoint:
        return tminidb().tv_series.similar


# TODO: Validate
class MoviesVideos(IntegerArgEndpointFile[MovieVideosModel]):
    custom_class_key = "Movies/Videos"

    # TODO: Validate
    @override
    def _endpoint(self) -> MovieVideosEndpoint:
        return tminidb().movie.videos


# TODO: Validate
class TVSeriesVideos(IntegerArgEndpointFile[TvSeriesVideosModel]):
    custom_class_key = "TV Series/Videos"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesVideosEndpoint:
        return tminidb().tv_series.videos


# TODO: Validate
class TVSeriesWatchProviders(IntegerArgEndpointFile[TvSeriesWatchProvidersModel]):
    custom_class_key = "TV Series/Watch Providers"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesWatchProvidersEndpoint:
        return tminidb().tv_series.watch_providers

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return staggered_yearly_update_at(self.file_key(), tz_datetime.now())


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
    @override
    def _next_update_at(self) -> datetime:
        return staggered_yearly_update_at(self.file_key(), tz_datetime.now())


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
def search_identifier(**parameters: str | int | None) -> str:
    return ", ".join(
        f"{name}={value}" for name, value in parameters.items() if value is not None
    )


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
        super().__init__(session, plugin, search_identifier(query=query, page=page))

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
        primary_release_year: int | None = None,
        year: int | None = None,
    ) -> None:
        self.query = query
        self.primary_release_year = primary_release_year
        self.year = year
        super().__init__(
            session,
            plugin,
            search_identifier(
                query=query,
                primary_release_year=primary_release_year,
                year=year,
            ),
        )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            self.query,
            primary_release_year=self.primary_release_year,
            year=self.year,
        )


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
        first_air_date_year: int | None = None,
        year: int | None = None,
    ) -> None:
        self.query = query
        self.first_air_date_year = first_air_date_year
        self.year = year
        super().__init__(
            session,
            plugin,
            search_identifier(
                query=query,
                first_air_date_year=first_air_date_year,
                year=year,
            ),
        )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            self.query,
            first_air_date_year=self.first_air_date_year,
            year=self.year,
        )


# TODO: Validate
class ChangesList[T: ChangesMovieListModel | ChangesTvListModel](
    PagedEndpointFile[T],
    ABC,
):
    keep_until_imported = True
    media_type: ClassVar[TMDBMediaType]

    # TODO: Validate
    @abstractmethod
    @override
    def _endpoint(  # type: ignore[override]
        self,
    ) -> ChangesMovieListEndpoint | ChangesTvListEndpoint: ...

    # TODO: Validate
    @override
    def _initial_status_after_downloading(self) -> str:
        return INCOMPLETE_STATUS

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + ROLLING_CHANGES_UPDATE_INTERVAL

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        start_datetime: datetime
        if self.exists():
            start_datetime = self.record_data_timestamp
        else:
            start_datetime = tz_datetime.now() - timedelta(days=1)
        return json.dumps(
            self._endpoint().download_all(
                start_datetime.astimezone(UTC).date(),
                tz_datetime.now().astimezone(UTC).date(),
            ),
        )

    # TODO: Validate
    def title_keys(self) -> set[str]:
        return {
            tmdb_title_key(self.media_type, result.id)
            for page in self.parsed()
            for result in page.results
        }


# TODO: Validate
class ChangesMovieList(ChangesList[ChangesMovieListModel]):
    custom_class_key = "Changes/Movie List"
    media_type = TMDBMediaType.movie

    # TODO: Validate
    @override
    def _endpoint(self) -> ChangesMovieListEndpoint:  # type: ignore[override]
        return tminidb().changes.movie_list


# TODO: Validate
class ChangesTVList(ChangesList[ChangesTvListModel]):
    custom_class_key = "Changes/TV List"
    media_type = TMDBMediaType.tv

    # TODO: Validate
    @override
    def _endpoint(self) -> ChangesTvListEndpoint:  # type: ignore[override]
        return tminidb().changes.tv_list


# TODO: Validate
class ExternalIds[T: MovieExternalIdsModel | TvSeriesExternalIdsModel](
    IntegerArgEndpointFile[T],
    ABC,
):
    _found = False

    # TODO: Validate
    @abstractmethod
    @override
    def _endpoint(  # type: ignore[override]
        self,
    ) -> MovieExternalIdsEndpoint | TvSeriesExternalIdsEndpoint: ...

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        content = super()._download_file()
        self._found = bool(self._parse(content).imdb_id)
        return content

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime | None:
        if self._found:
            return None
        return staggered_yearly_update_at(self.file_key(), tz_datetime.now())

    # TODO: Validate
    def imdb_id(self) -> str | None:
        if self.record_content is None:
            return None
        return self.parsed().imdb_id or None


# TODO: Validate
class MoviesExternalIds(ExternalIds[MovieExternalIdsModel]):
    custom_class_key = "Movies/External IDs"

    # TODO: Validate
    @override
    def _endpoint(self) -> MovieExternalIdsEndpoint:
        return tminidb().movie.external_ids


# TODO: Validate
class TVSeriesExternalIds(ExternalIds[TvSeriesExternalIdsModel]):
    custom_class_key = "TV Series/External IDs"

    # TODO: Validate
    @override
    def _endpoint(self) -> TvSeriesExternalIdsEndpoint:
        return tminidb().tv_series.external_ids


# TODO: Validate
class FindByIMDbId(MultipleArgEndpointFile[FindByIdModel]):
    custom_class_key = "Find/IMDb ID"
    _found = False

    # TODO: Validate
    @override
    def _endpoint(self) -> FindByIdEndpoint:
        return tminidb().find.by_id

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        content = self._endpoint().download(self.unique_identifier, "imdb_id")
        found = self._endpoint().load(content, self.log_id())
        self._found = bool(found.movie_results or found.tv_results)
        return content

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime | None:
        if self._found:
            return None
        return staggered_yearly_update_at(self.file_key(), tz_datetime.now())


# TODO: Validate
class IMDbTitle(SingleArgEndpointFile[IMDbTitleModel]):
    custom_class_key = "IMDb/Title"

    # TODO: Validate
    @override
    def _endpoint(self) -> IMDbTitleEndpoint:
        return i_am_the_db().title

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, TitleNotFoundError)

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return staggered_yearly_update_at(self.file_key(), tz_datetime.now())
