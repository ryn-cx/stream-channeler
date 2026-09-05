# TODO: Validate
from __future__ import annotations

from plugins.ParamountPlus.files import EpisodesFile, MovieFile, ShowPage
from plugins.utils.base_plugin_v3.base import BasePlugin


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def show_page_file(self, show_id: str) -> ShowPage:
        return self._file(ShowPage, show_id)

    # TODO: Validate
    def episodes_file(self, show_id: str, season_number: int) -> EpisodesFile:
        return self._file(EpisodesFile, show_id, season_number)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        return self._file(MovieFile, movie_id)
