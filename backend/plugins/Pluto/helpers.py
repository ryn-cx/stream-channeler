# TODO: Validate
from typing import override
from urllib.parse import quote

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.Pluto.files import FileMixin

# The website serves every on-demand page under a locale segment.
_LOCALE = "en"


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
        if existing_show and existing_show.tmdb_id is not None:
            return existing_show.tmdb_id
        if self._is_movie():
            self.items_file(show_key).download_if_outdated()
            return self._tmdb_search_media(self._item(show_key).name, MediaType.movie)
        self.seasons_file(show_key).download_if_outdated()
        return self._tmdb_search_media(self._series(show_key).name, MediaType.tv)

    @override
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if self._is_movie() else MediaType.tv

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
            if episode.field_id == episode_key:
                return episode.number
        return None

    @classmethod
    def _series_url(cls, show_key: str) -> str:
        return cls.build_url(f"{_LOCALE}/on-demand/series/{show_key}/details")

    @classmethod
    def _movie_url(cls, show_key: str) -> str:
        return cls.build_url(f"{_LOCALE}/on-demand/movies/{show_key}/details")

    @classmethod
    def _season_url(cls, show_key: str, season_number: int) -> str:
        return cls.build_url(
            f"{_LOCALE}/on-demand/series/{show_key}/season/{season_number}",
        )

    @classmethod
    def _episode_url(
        cls,
        show_key: str,
        season_number: int,
        episode_key: str,
    ) -> str:
        return cls.build_url(
            f"{_LOCALE}/on-demand/series/{show_key}/season/{season_number}"
            f"/episode/{episode_key}",
        )

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"{_LOCALE}/search?query={quote(query)}")
