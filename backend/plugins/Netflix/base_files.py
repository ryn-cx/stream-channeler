# TODO: Validate
from __future__ import annotations

from plugins.Netflix.files import (
    LodpTitleAndPlansPage,
    PreviewModalEpisodeSelector,
    PreviewModalEpisodeSelectorSeasonEpisodes,
    SearchPageResults,
)
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class NetflixBaseFiles(BasePlugin):
    # TODO: Validate
    def title_file(self, title_key: str) -> LodpTitleAndPlansPage:
        return self._file(LodpTitleAndPlansPage, title_key)

    # TODO: Validate
    def seasons_file(self, title_key: str) -> PreviewModalEpisodeSelector:
        return self._file(PreviewModalEpisodeSelector, title_key)

    # TODO: Validate
    def season_episodes_file(
        self,
        season_video_key: str | int,
    ) -> PreviewModalEpisodeSelectorSeasonEpisodes:
        return self._file(
            PreviewModalEpisodeSelectorSeasonEpisodes,
            str(season_video_key),
        )

    # TODO: Validate
    def search_file(self, query: str) -> SearchPageResults:
        return self._file(SearchPageResults, query)
