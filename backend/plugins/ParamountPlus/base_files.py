# TODO: Validate
from __future__ import annotations

from plugins.ParamountPlus.files import (
    EpisodesFile,
    MovieFile,
    TitlePage,
)
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class ParamountPlusBaseFiles(BasePlugin):
    # TODO: Validate
    def title_page_file(self, title_id: str) -> TitlePage:
        return self._cached_file(TitlePage, title_id)

    # TODO: Validate
    def episodes_file(
        self,
        title_id: str,
        season_number: int,
    ) -> EpisodesFile:
        return self._cached_file(EpisodesFile, title_id, season_number)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        return self._cached_file(MovieFile, movie_id)
