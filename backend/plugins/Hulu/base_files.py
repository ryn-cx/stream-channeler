from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Hulu.files import (
    AllMovies,
    AllSeries,
    Episode,
    Movie,
    Search,
    Season,
    Series,
    WatchRedirect,
)
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO: Validate
class HuluBaseFiles(BasePlugin):
    # TODO: Validate
    def search_file(self, query: str) -> Search:
        return self._file(Search, query)

    # TODO: Validate
    def watch_redirect_file(self, episode_key: str) -> WatchRedirect:
        return self._file(WatchRedirect, episode_key)

    # TODO: Validate
    def all_series_file(self) -> AllSeries:
        return self._file(AllSeries, "all_series")

    # TODO: Validate
    def all_movies_file(self) -> AllMovies:
        return self._file(AllMovies, "all_movies")

    # TODO: Validate
    def series_file(self, series_id: str) -> Series:
        return self._file(Series, series_id)

    # TODO: Validate
    def episode_file(self, episode_id: str) -> Episode:
        return self._file(Episode, episode_id)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> Movie:
        return self._file(Movie, movie_id)

    # TODO: Validate
    def season_file(self, series_id: str, season_number: int) -> Season:
        return self._file(Season, series_id, season_number)

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[AllSeries | AllMovies]:
        return [self.all_series_file(), self.all_movies_file()]
