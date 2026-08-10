# TODO: Validate
from typing import override

from chirashi.series import models as series_models

from app.media.media_type import MediaType
from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll.files import FileMixin
from plugins.Crunchyroll.music_keys import (
    is_music_episode_key,
    is_music_season_key,
    is_music_show_key,
    music_episode_category,
)


class HelperMixin(FileMixin, register=False):
    video_source: Source
    music_source: Source

    def _source_from_show_key(self, show_key: str) -> Source:
        if is_music_show_key(show_key):
            return self.music_source
        return self.video_source

    def _series_datum(self, show_key: str) -> series_models.Datum:
        series_file = self.series_file(show_key)
        return series_file.parsed().data[0]

    def _is_movie(self, show_key: str) -> bool:
        return "type:movie" in self._series_datum(show_key).keywords

    @override
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if self._is_movie(show_key) else MediaType.tv

    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        # TMDB catalogues films and series, so an artist has nothing to match.
        if is_music_show_key(show_key):
            return None
        series = self._series_datum(show_key)
        return self._tmdb_search_media(
            series.title,
            self.tmdb_media_type(show_key),
            series.series_launch_year,
        )

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        if is_music_season_key(season_key):
            return None
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
        if is_music_season_key(season_key):
            return None
        for episode_data in self.season_episodes_file(season_key).parsed().data:
            if episode_data.id == episode_key:
                return episode_data.episode_number
        return None

    @classmethod
    def _series_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    @classmethod
    def _artist_url(cls, show_key: str) -> str:
        return cls.build_url(f"artist/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        # Crunchyroll files a music video or a concert under the listing it
        # belongs to, which its id says but the url still has to be told.
        if is_music_episode_key(episode_key):
            category = music_episode_category(episode_key)
            return cls.build_url(f"watch/{category}/{episode_key}")
        return cls.build_url(f"watch/{episode_key}")
