from __future__ import annotations

from plugins.Netflix.files import (
    DetailModal,
    LodpTitleAndPlansPage,
    PreviewModalEpisodeSelector,
    PreviewModalEpisodeSelectorSeasonEpisodes,
)
from plugins.utils.base_plugin.base import BasePlugin


class NetflixBaseFiles(BasePlugin):
    def similar_file(self, title_key: str) -> LodpTitleAndPlansPage:
        return self._cached_file(LodpTitleAndPlansPage, title_key)

    # TODO: Validate
    def title_file(self, title_key: str) -> DetailModal:
        return self._cached_file(DetailModal, title_key)

    def seasons_file(self, title_key: str) -> PreviewModalEpisodeSelector:
        return self._cached_file(PreviewModalEpisodeSelector, title_key)

    def season_episodes_file(
        self,
        season_video_key: str | int,
    ) -> PreviewModalEpisodeSelectorSeasonEpisodes:
        return self._cached_file(
            PreviewModalEpisodeSelectorSeasonEpisodes,
            str(season_video_key),
        )
