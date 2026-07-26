# TODO: Validate
from typing import Literal, override

from app.shows.models import Show
from plugins.Amazon.files import FileMixin


class HelperMixin(FileMixin, register=False):
    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        self.detail_page(show_key).download_if_outdated()
        page = self.detail_page(show_key)
        if self._is_movie(show_key):
            return self._tmdb_search_media(page.title(), "movie")
        return self._tmdb_search_media(page.series_title())

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie(show_key) else "tv"

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        for season in self._season_entries(show_key):
            if season.asin == season_key:
                return season.season_number
        return None

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        for episode in self.detail_page(season_key).episodes():
            if episode.asin == episode_key:
                return episode.episode_number
        return None
