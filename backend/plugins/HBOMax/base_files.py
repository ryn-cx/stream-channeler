# TODO: Validate
from __future__ import annotations

from plugins.HBOMax.files import MovieFile, SeasonFile, TitleFile
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class HBOMaxBaseFiles(BasePlugin):
    # TODO: Validate
    def title_file(self, title_id: str) -> TitleFile:
        return self._cached_file(TitleFile, title_id)

    # TODO: Validate
    def season_file(self, title_id: str, season_number: int) -> SeasonFile:
        return self._cached_file(SeasonFile, title_id, season_number)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        return self._cached_file(MovieFile, movie_id)
