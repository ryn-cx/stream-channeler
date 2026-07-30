# TODO: Validate
from typing import Literal, override

from app.shows.models import Show
from plugins.Netflix.files import FileMixin


class HelperMixin(FileMixin, register=False):
    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id is not None:
            return existing_show.tmdb_id
        self.title_file(show_key).download_if_outdated()
        media_type: Literal["movie", "tv"]
        if self._is_movie(show_key):
            media_type = "movie"
        else:
            media_type = "tv"
        return self._tmdb_search_media(self._title_video(show_key).title, media_type)

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie(show_key) else "tv"

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        _, season_id = self._split_season_key(season_key)
        for index, season in enumerate(self._ordered_seasons(show_key)):
            if str(season.video_id) == season_id:
                return index + 1
        return None

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        _, season_id = self._split_season_key(season_key)
        for episode in self._season_episodes(show_key, int(season_id)):
            if str(episode.video_id) == episode_key:
                return episode.number
        return None

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"title/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")
