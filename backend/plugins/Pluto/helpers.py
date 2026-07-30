# TODO: Validate
from typing import Literal, override

from app.shows.models import Show
from plugins.Pluto.files import FileMixin


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
            return self._tmdb_search_media(self._item(show_key).name, "movie")
        self.seasons_file(show_key).download_if_outdated()
        return self._tmdb_search_media(self._series(show_key).name, "tv")

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie() else "tv"

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
