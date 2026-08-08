# TODO: Validate
from typing import override

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.Roku.files import FileMixin, content_id


class HelperMixin(FileMixin, register=False):
    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id is not None:
            return existing_show.tmdb_id
        self.content_file(show_key).download_if_outdated()
        media_type: MediaType
        if self._is_movie(show_key):
            media_type = MediaType.movie
        else:
            media_type = MediaType.tv
        content = self._content(show_key)
        return self._tmdb_search_media(content.title, media_type, content.release_year)

    @override
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if self._is_movie(show_key) else MediaType.tv

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        _, season_number = self._split_season_key(season_key)
        return season_number

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        if self._is_movie(show_key):
            return 0
        _, season_number = self._split_season_key(season_key)
        for episode in self._season_episodes(show_key, season_number):
            if content_id(episode.meta.id) == episode_key:
                return int(episode.episode_number)
        return None

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"details/{show_key}")

    @classmethod
    def _video_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url("search")
