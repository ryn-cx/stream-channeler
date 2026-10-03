# TODO: Validate
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, NamedTuple, override

from sqlmodel import select

from app.media.media_type import TMDBMediaType
from app.titles.models import Title
from app.tmdb_media.tmdb import (
    get_media_type_and_tmdb_id,
    tmdb_title_key,
)
from app.utils import tz_datetime
from plugins.TMDB.files import (
    ChangesMovieList,
    ChangesTVList,
    FindByIMDbId,
    IMDbTitle,
    MoviesExternalIds,
    MoviesRecommendations,
    MoviesWatchProviders,
    SearchMovie,
    SearchMulti,
    SearchTV,
    TVSeasonsWatchProviders,
    TVSeriesExternalIds,
    TVSeriesRecommendations,
    TVSeriesWatchProviders,
)
from plugins.TMDB.movie_importer import TMDBMovie
from plugins.TMDB.series_importer import TMDBSeries
from plugins.TMDB.shared import TMDBImporter, TMDBPluginShared, TMDBSearch
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.updater import BasePluginUpdater
from plugins.utils.constants import INCOMPLETE_STATUS

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from app.files.models import File
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class TMDBSearchResult(NamedTuple):
    media_type: TMDBMediaType
    tmdb_id: int
    names: list[str]
    years: list[int]
    overview: str | None


# TODO: Validate
class TMDBUpdater(TMDBPluginShared, TMDBSearch, BasePluginUpdater):
    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        return []

    # TODO: Validate
    @override
    def update_file(self, file: File) -> None:
        if file.update_at and file.update_at > tz_datetime.now():
            return
        if file.key.startswith(f"{MoviesWatchProviders.class_key()}/"):
            tmdb_id = int(MoviesWatchProviders.file_to_unique_identifier(file))
            self._update_title_watch_providers(TMDBMediaType.movie, tmdb_id)
            return
        if file.key.startswith(f"{TVSeriesWatchProviders.class_key()}/"):
            tmdb_id = int(TVSeriesWatchProviders.file_to_unique_identifier(file))
            self._update_title_watch_providers(TMDBMediaType.tv, tmdb_id)
            return
        if file.key.startswith(f"{TVSeasonsWatchProviders.class_key()}/"):
            series_id, season_number = (
                TVSeasonsWatchProviders.file_to_unique_identifier(
                    file,
                ).split("/")
            )
            self._cached_file(
                TVSeasonsWatchProviders,
                int(series_id),
                int(season_number),
            ).download_if_outdated()
            return
        for file_class in (
            MoviesExternalIds,
            TVSeriesExternalIds,
            FindByIMDbId,
            IMDbTitle,
        ):
            if file.key.startswith(f"{file_class.class_key()}/"):
                self._cached_file(
                    file_class,
                    file_class.file_to_unique_identifier(file),
                ).download_if_outdated()
                return
        super().update_file(file)

    # TODO: Validate
    def _update_title_watch_providers(
        self,
        media_type: TMDBMediaType,
        tmdb_id: int,
    ) -> None:
        importer = self._get_media_importer_from_media_type(media_type)
        providers_file = (
            importer.movies_watch_providers_file(tmdb_id)
            if media_type == TMDBMediaType.movie
            else importer.tv_series_watch_providers_file(tmdb_id)
        )
        providers_file.download_if_outdated()
        title = self.session.exec(
            select(Title).where(
                Title.source_id == self.source.id,
                Title.key == tmdb_title_key(media_type, tmdb_id),
            ),
        ).one_or_none()
        if title is None or title.deleted_at or providers_file.record_content is None:
            return
        importer.record_providers(title, providers_file.parsed())

    # TODO: Validate
    def find_by_imdb_id_file(self, imdb_id: str) -> FindByIMDbId:
        return self._cached_file(FindByIMDbId, imdb_id)

    # TODO: Validate
    def tmdb_url_from_imdb_id(self, imdb_id: str) -> str:
        find_file = self.find_by_imdb_id_file(imdb_id)
        find_file.download_if_outdated()
        found = find_file.parsed()
        if found.movie_results:
            return self.tmdb_url(TMDBMediaType.movie, found.movie_results[0].id)
        if found.tv_results:
            return self.tmdb_url(TMDBMediaType.tv, found.tv_results[0].id)
        msg = f"TMDB has no movie or TV show for the IMDb title {imdb_id}."
        raise InvalidURLError(msg)

    # TODO: Validate
    def changes_movie_list_file(self) -> ChangesMovieList:
        return self._cached_file(ChangesMovieList)

    # TODO: Validate
    def changes_tv_list_file(self) -> ChangesTVList:
        return self._cached_file(ChangesTVList)

    # TODO: Validate
    @override
    def _plugin_files(self) -> Sequence[ChangesMovieList | ChangesTVList]:
        return [self.changes_movie_list_file(), self.changes_tv_list_file()]

    # TODO: Validate
    @override
    def _import_plugin_files(self) -> None:
        _cache = self._preload_sources(self.source_name(), preload_seasons=True).all()
        for changes_file in self._plugin_files():
            if changes_file.record_status != INCOMPLETE_STATUS:
                continue
            update_at = changes_file.record_data_timestamp + timedelta(days=7)
            for title_key in changes_file.title_keys():
                if title := Title.get_from_memory(self.session, self.source, title_key):
                    title.set_update_at(update_at)
                    for season in title.seasons:
                        season.set_update_at(update_at)
            changes_file.clear_status()

    # TODO: Validate
    def _get_media_importer_from_media_type(
        self,
        media_type: TMDBMediaType,
    ) -> TMDBImporter:
        if media_type == TMDBMediaType.movie:
            return TMDBMovie(self.session, self.plugin, self._file_cache)
        return TMDBSeries(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    def movies_recommendations_file(
        self,
        tmdb_movie_id: int,
    ) -> MoviesRecommendations:
        return self._cached_file(MoviesRecommendations, tmdb_movie_id)

    # TODO: Validate
    def tv_series_recommendations_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesRecommendations:
        return self._cached_file(TVSeriesRecommendations, tmdb_tv_title_id)

    # TODO: Validate
    def _recommendations_file(
        self,
        title_key: str,
    ) -> MoviesRecommendations | TVSeriesRecommendations:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(title_key)
        if media_type == TMDBMediaType.movie:
            return self.movies_recommendations_file(tmdb_media_id)
        return self.tv_series_recommendations_file(tmdb_media_id)

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:
        media_type, _ = get_media_type_and_tmdb_id(title.key)
        # This file is only ever used when a user wants a channel built upon a single
        # show. It's usage is so niche it's easier to just download the recommendations
        # file on demand.
        self._download_if_outdated(
            [self._recommendations_file(title.key)],
            tz_datetime.now() - timedelta(days=30),
        )
        return [
            self.tmdb_url(media_type, result.id)
            for result in self._recommendations_file(title.key).parsed().results
        ]

    # TODO: Validate
    def search_movie_file(
        self,
        query: str,
        exact_year: int | None = None,
        rough_year: int | None = None,
    ) -> SearchMovie:
        return self._cached_file(SearchMovie, query, exact_year, rough_year)

    # TODO: Validate
    def search_tv_file(
        self,
        query: str,
        exact_year: int | None = None,
        rough_year: int | None = None,
    ) -> SearchTV:
        return self._cached_file(SearchTV, query, exact_year, rough_year)

    # TODO: Validate
    def _search_file(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        exact_year: int | None,
        rough_year: int | None,
    ) -> SearchMovie | SearchTV | SearchMulti:
        if media_type == TMDBMediaType.movie:
            return self.search_movie_file(query, exact_year, rough_year)
        if media_type == TMDBMediaType.tv:
            return self.search_tv_file(query, exact_year, rough_year)
        return self.search_multi_file(query)

    # TODO: Validate
    def _download_search_file(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        exact_year: int | None,
        rough_year: int | None,
    ) -> None:
        self._download_if_outdated(
            [self._search_file(media_type, query, exact_year, rough_year)],
        )

    # TODO: Validate
    def search(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        exact_year: int | None,
        rough_year: int | None,
    ) -> list[TMDBSearchResult]:
        self._download_search_file(media_type, query, exact_year, rough_year)
        search_file = self._search_file(media_type, query, exact_year, rough_year)
        search_results: list[TMDBSearchResult] = []
        for result in search_file.parsed().results:
            result_media_type = media_type or getattr(result, "media_type", None)
            if result_media_type not in set(TMDBMediaType):
                continue
            search_results.append(
                TMDBSearchResult(
                    media_type=TMDBMediaType(result_media_type),
                    tmdb_id=result.id,
                    names=[
                        result_name
                        for field in (
                            "name",
                            "original_name",
                            "title",
                            "original_title",
                        )
                        if isinstance(result_name := getattr(result, field, None), str)
                    ],
                    years=[
                        result_date.year
                        for field in ("release_date", "first_air_date")
                        if isinstance(result_date := getattr(result, field, None), date)
                    ],
                    overview=result.overview or None,
                ),
            )
        return search_results

    # TODO: Validate
    def import_search_result(
        self,
        search_result: TMDBSearchResult,
    ) -> list[URLImportResult]:
        existing_title = self.session.exec(
            select(Title).where(
                Title.source_id == self.source.id,
                Title.key
                == tmdb_title_key(search_result.media_type, search_result.tmdb_id),
            ),
        ).one_or_none()
        if existing_title and existing_title.deleted_at:
            return []
        media_importer = self._get_media_importer_from_media_type(
            search_result.media_type,
        )
        return media_importer.import_url(
            self.tmdb_url(search_result.media_type, search_result.tmdb_id),
        )
