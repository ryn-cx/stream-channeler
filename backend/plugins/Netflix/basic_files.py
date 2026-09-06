# TODO: Validate
from __future__ import annotations

from plugins.Netflix.files import Search, SeasonEpisodes, Seasons, Title
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def title_file(self, title_key: str) -> Title:
        return self._file(Title, title_key)

    # TODO: Validate
    def seasons_file(self, title_key: str) -> Seasons:
        return self._file(Seasons, title_key)

    # TODO: Validate
    def season_episodes_file(self, season_id: str | int) -> SeasonEpisodes:
        return self._file(SeasonEpisodes, str(season_id))

    # TODO: Validate
    def search_file(self, query: str, cursor: str | None) -> Search:
        return self._file(Search, query, cursor or "")
