# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Hulu.files import (
    Episode,
    Genre,
    Genres,
    Movie,
    Season,
    Series,
    WatchRedirect,
)
from plugins.Hulu.utils import listed_items
from plugins.utils.base_plugin_v3.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence


class BasicFiles(BasePlugin):
    def watch_redirect_file(self, episode_key: str) -> WatchRedirect:
        return self._file(WatchRedirect, episode_key)

    def genres_file(self) -> Genres:
        return self._file(Genres, "genres")

    def genre_file(self, genre_id: str) -> Genre:
        return self._file(Genre, genre_id)

    def series_file(self, series_id: str) -> Series:
        return self._file(Series, series_id)

    def episode_file(self, episode_id: str) -> Episode:
        return self._file(Episode, episode_id)

    def movie_file(self, movie_id: str) -> Movie:
        return self._file(Movie, movie_id)

    def season_file(self, series_id: str, season_number: int) -> Season:
        return self._file(Season, series_id, season_number)

    @override
    def _source_files(self) -> Sequence[Genres | Genre]:
        genres_page = self.genres_file()
        return [
            genres_page,
            *(
                self.genre_file(href.rsplit("/", 1)[-1])
                for _name, href in listed_items(genres_page.parsed())
            ),
        ]
