# TODO: Validate
from __future__ import annotations

from plugins.TMDB.files import (
    MoviesDetails,
    MoviesRecommendations,
    MoviesSimilar,
    MoviesWatchProviders,
    SearchMovie,
    SearchMulti,
    SearchTV,
    TVEpisodeGroupsDetails,
    TVSeasonsDetails,
    TVSeasonsWatchProviders,
    TVSeriesDetails,
    TVSeriesEpisodeGroups,
    TVSeriesImages,
    TVSeriesRecommendations,
    TVSeriesSimilar,
    TVSeriesWatchProviders,
)
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class TMDBBaseFiles(BasePlugin):
    # TODO: Validate
    def search_multi_file(self, query: str, page: int = 1) -> SearchMulti:
        return self._cached_file(SearchMulti, query, page)

    # TODO: Validate
    def search_movie_file(self, query: str, year: int | None = None) -> SearchMovie:
        return self._cached_file(SearchMovie, query, year)

    # TODO: Validate
    def search_tv_file(self, query: str, year: int | None = None) -> SearchTV:
        return self._cached_file(SearchTV, query, year)

    # TODO: Validate
    def movies_details_file(self, tmdb_movie_id: int) -> MoviesDetails:
        return self._cached_file(MoviesDetails, str(tmdb_movie_id))

    # TODO: Validate
    def tv_series_details_file(self, tmdb_tv_title_id: int) -> TVSeriesDetails:
        return self._cached_file(TVSeriesDetails, tmdb_tv_title_id)

    # TODO: Validate
    def tv_series_images_file(self, tmdb_tv_title_id: int) -> TVSeriesImages:
        return self._cached_file(TVSeriesImages, tmdb_tv_title_id)

    # TODO: Validate
    def tv_series_episode_groups_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesEpisodeGroups:
        return self._cached_file(TVSeriesEpisodeGroups, tmdb_tv_title_id)

    # TODO: Validate
    def tv_episode_groups_details_file(
        self,
        group_id: str,
    ) -> TVEpisodeGroupsDetails:
        return self._cached_file(TVEpisodeGroupsDetails, group_id)

    # TODO: Validate
    def tv_seasons_details_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsDetails:
        return self._cached_file(TVSeasonsDetails, tmdb_tv_title_id, season_number)

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
    def movies_similar_file(self, tmdb_movie_id: int) -> MoviesSimilar:
        return self._cached_file(MoviesSimilar, tmdb_movie_id)

    # TODO: Validate
    def tv_series_similar_file(self, tmdb_tv_title_id: int) -> TVSeriesSimilar:
        return self._cached_file(TVSeriesSimilar, tmdb_tv_title_id)

    # TODO: Validate
    def movies_watch_providers_file(self, tmdb_movie_id: int) -> MoviesWatchProviders:
        return self._cached_file(MoviesWatchProviders, tmdb_movie_id)

    # TODO: Validate
    def tv_series_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesWatchProviders:
        return self._cached_file(TVSeriesWatchProviders, tmdb_tv_title_id)

    # TODO: Validate
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsWatchProviders:
        return self._cached_file(
            TVSeasonsWatchProviders,
            tmdb_tv_title_id,
            season_number,
        )
