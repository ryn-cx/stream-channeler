# TODO: Validate
from __future__ import annotations

from plugins.HBOMax.files import MovieFile, SeasonFile, ShowFile
from plugins.utils.base_plugin_v3.base import BasePlugin


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def show_file(self, show_id: str) -> ShowFile:
        return self._file(ShowFile, show_id)

    # TODO: Validate
    def season_file(self, show_id: str, season_number: int) -> SeasonFile:
        return self._file(SeasonFile, show_id, season_number)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        return self._file(MovieFile, movie_id)
