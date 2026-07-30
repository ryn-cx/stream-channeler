# TODO: Validate
from datetime import timedelta
from typing import Literal

from tminidb.movie_details.models import MovieDetailsModel

from app.utils import tz_datetime
from plugins.TMDB.files import (
    FileMixin,
    MovieSearch,
    MovieWatchProviders,
    MultiSearch,
    TvSearch,
    TvWatchProviders,
)

_SEARCH_MAX_AGE = timedelta(days=7)


_MEDIA_INFO_MAX_AGE = timedelta(days=7)


class LookupMixin(FileMixin, register=False):
    def auto_updating_search_media(
        self,
        media_type: Literal["movie", "tv"] | None,
        query: str,
        year: int | None = None,
    ) -> MovieSearch | TvSearch | MultiSearch:
        search_file: MovieSearch | TvSearch | MultiSearch
        if media_type == "movie":
            search_file = self.movie_search_file(query, year)
        elif media_type == "tv":
            search_file = self.tv_search_file(query, year)
        else:
            search_file = self.multi_search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)
        return search_file

    def auto_updating_watch_providers(
        self,
        media_type: Literal["movie", "tv"],
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders:
        providers_file = self.watch_providers_file(media_type, tmdb_id)
        providers_file.download_if_outdated(tz_datetime.now() - _MEDIA_INFO_MAX_AGE)
        return providers_file

    def _movie_detail(self, tmdb_id: int) -> MovieDetailsModel | None:
        return self.media_detail_file("movie", tmdb_id).parsed()

    def has_season(self, tmdb_id: int, season_number: int) -> bool:
        show_detail = self.show_detail_file(tmdb_id).parsed()
        return any(
            season.season_number == season_number for season in show_detail.seasons
        )

    def has_episode(
        self,
        tmdb_id: int,
        season_number: int,
        episode_number: int,
    ) -> bool:
        if not self.has_season(tmdb_id, season_number):
            return False
        season_detail = self.season_detail_file(tmdb_id, season_number).parsed()
        return any(
            episode.episode_number == episode_number
            for episode in season_detail.episodes
        )
