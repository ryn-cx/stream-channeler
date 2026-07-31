# TODO: Validate
from typing import Literal, override

from chirashi.series import models as series_models

from app.shows.models import Show
from plugins.Crunchyroll.files import FileMixin


class HelperMixin(FileMixin, register=False):
    def _series_datum(self, show_key: str) -> series_models.Datum:
        series_file = self.series_file(show_key)
        return series_file.parsed().data[0]

    def _is_movie(self, show_key: str) -> bool:
        return "type:movie" in self._series_datum(show_key).keywords

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie(show_key) else "tv"

    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        series = self._series_datum(show_key)
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

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")
