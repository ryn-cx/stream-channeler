# TODO: Validate
import re
from typing import Literal, override
from urllib.parse import quote

from app.shows.models import Show
from plugins.Tubi.files import FileMixin

# Episode titles are prefixed with their season and episode number, e.g.
# "S01:E01 - What a Night for a Knight".
_EPISODE_TITLE_PREFIX_REGEX = re.compile(r"^S\d+:E\d+ - ")


class HelperMixin(FileMixin, register=False):
    @staticmethod
    def _episode_name(title: str) -> str:
        return _EPISODE_TITLE_PREFIX_REGEX.sub("", title)

    @staticmethod
    def _first_image(images: list[str]) -> str | None:
        return images[0] if images else None

    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id is not None:
            return existing_show.tmdb_id
        self.content_file(show_key).download_if_outdated()
        media_type: Literal["movie", "tv"]
        if self._is_movie(show_key):
            media_type = "movie"
        else:
            media_type = "tv"
        return self._tmdb_search_media(self._content(show_key).title, media_type)

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie(show_key) else "tv"

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        _, season_id = self._split_season_key(season_key)
        return int(season_id)

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        _, season_id = self._split_season_key(season_key)
        for episode in self._season_episodes(show_key, season_id):
            if episode.id == episode_key:
                return int(episode.episode_number)
        return None

    @classmethod
    def _series_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    @classmethod
    def _movie_url(cls, show_key: str) -> str:
        return cls.build_url(f"movies/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"tv-shows/{episode_key}")

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"search/{quote(query)}")
