# TODO: Validate
import re
from typing import Literal, override

from app.shows.models import Show
from plugins.DisneyPlus.files import FileMixin

# Season names are the only place the real season number appears, the position of a
# season in the list is not reliable because shows can start at a season other than 1.
_SEASON_NUMBER_REGEX = re.compile(r"\d+")


class HelperMixin(FileMixin, register=False):
    @staticmethod
    def _season_number_from_name(name: str, fallback: int) -> int:
        if number := _SEASON_NUMBER_REGEX.search(name):
            return int(number.group())
        return fallback

    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id is not None:
            return existing_show.tmdb_id
        self.entity_file(show_key).download_if_outdated()
        media_type: Literal["movie", "tv"]
        if self._is_movie(show_key):
            media_type = "movie"
        else:
            media_type = "tv"
        return self._tmdb_search_media(self._media_details(show_key).title, media_type)

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie(show_key) else "tv"

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        _, season_id = self._split_season_key(season_key)
        for index, season in enumerate(self._seasons(show_key)):
            if str(season.id) == season_id:
                return self._season_number_from_name(season.name, index + 1)
        return None

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        _, season_id = self._split_season_key(season_key)
        for index, episode in enumerate(self._season_episodes(show_key, season_id)):
            if str(episode.field_id) == episode_key:
                return index + 1
        return None
