# TODO: Validate
from typing import Literal, override

from app.shows.models import Show
from plugins.ParamountPlus.files import FileMixin


class HelperMixin(FileMixin, register=False):
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = "movie" if show.media_type == "Movie" else "series"

    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        if self._is_movie():
            self.movie_file(show_key).download_if_outdated()
            return self._tmdb_search_media(self._movie_model(show_key).name, "movie")
        self.show_page_file(show_key).download_if_outdated()
        return self._tmdb_search_media(self._series_title(show_key))

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
        _, season_number = self._split_season_key(season_key)
        for episode in self._season_episodes(show_key, season_number):
            if episode.content_id == episode_key:
                return int(episode.episode_number)
        return None

    @override
    def tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie() else "tv"

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"shows/{show_key}/")

    @classmethod
    def _movie_url(cls, movie_key: str) -> str:
        return cls.build_url(f"movies/video/{movie_key}/")

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url("search/")
