from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Hulu.files import (
    AllMovies,
    AllSeries,
    Episode,
    Genre,
    Genres,
    Movie,
    Search,
    Season,
    Series,
)
from plugins.Hulu.utils import genre_ids
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence


class HuluBaseFiles(BasePlugin):
    def search_file(self, query: str) -> Search:
        return self._cached_file(Search, query)

    # TODO: Validate
    def episode_file(self, episode_key: str) -> Episode:
        return self._cached_file(Episode, episode_key)

    def all_series_file(self) -> AllSeries:
        return self._cached_file(AllSeries)

    def all_movies_file(self) -> AllMovies:
        return self._cached_file(AllMovies)

    def genres_file(self) -> Genres:
        return self._cached_file(Genres)

    def genre_file(self, genre_id: str) -> Genre:
        return self._cached_file(Genre, genre_id)

    def genre_files(self) -> list[Genre]:
        self.genres_file().download_if_outdated()
        return [
            self.genre_file(genre_id)
            for genre_id in genre_ids(self.genres_file().parsed())
        ]

    def series_file(self, series_id: str) -> Series:
        return self._cached_file(Series, series_id)

    def movie_file(self, movie_id: str) -> Movie:
        return self._cached_file(Movie, movie_id)

    def season_file(self, series_id: str, season_number: int) -> Season:
        return self._cached_file(Season, series_id, season_number)

    @override
    def _plugin_files(self) -> Sequence[AllSeries | AllMovies | Genres | Genre]:
        return [
            self.all_series_file(),
            self.all_movies_file(),
            self.genres_file(),
            *self.genre_files(),
        ]
