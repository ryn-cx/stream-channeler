# TODO: Validate
from typing import Literal, override

from app.shows.models import Show
from plugins.Crunchyroll.files import FileMixin


class HelperMixin(FileMixin, register=False):
    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        self.series_file(show_key).download_if_outdated()
        series = self.series_file(show_key).parsed().data[0]
        return "movie" if "type:movie" in series.keywords else "tv"

    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        self.series_file(show_key).download_if_outdated()
        series = self.series_file(show_key).parsed().data[0]
        return self._tmdb_search_media(
            series.title,
            self._tmdb_media_type(show_key),
            series.series_launch_year,
        )

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        for season_data in self.seasons_file(show_key).parsed().data:
            if season_data.id == season_key:
                return season_data.season_number
        msg = f"Season with key {season_key} not found for show {show_key}"
        raise ValueError(msg)

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        for episode_data in self.season_episodes_file(season_key).parsed().data:
            if episode_data.id == episode_key:
                return episode_data.episode_number
        return None
