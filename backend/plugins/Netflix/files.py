# TODO: Validate
from __future__ import annotations

from functools import cache
from typing import override

from meshfilm import Meshfilm
from meshfilm.lodp_title_and_plans_page import (
    LodpTitleAndPlansPage as LodpTitleAndPlansPageEndpoint,
)
from meshfilm.lodp_title_and_plans_page.models import LodpTitleAndPlansPageModel
from meshfilm.lodp_title_and_plans_page.models import Video1 as TitleVideo
from meshfilm.preview_modal_episode_selector import (
    PreviewModalEpisodeSelector as PreviewModalEpisodeSelectorEndpoint,
)
from meshfilm.preview_modal_episode_selector.models import (
    Node as SeasonNode,
)
from meshfilm.preview_modal_episode_selector.models import (
    PreviewModalEpisodeSelectorModel,
)
from meshfilm.preview_modal_episode_selector_season_episodes import (
    PreviewModalEpisodeSelectorSeasonEpisodes as PreviewModalEpisodeSelectorSeasonEpisodesEndpoint,
)
from meshfilm.preview_modal_episode_selector_season_episodes.models import (
    Node as EpisodeNode,
)
from meshfilm.preview_modal_episode_selector_season_episodes.models import (
    PreviewModalEpisodeSelectorSeasonEpisodesModel,
)
from meshfilm.search_page_results import SearchPageResults as SearchPageResultsEndpoint
from meshfilm.search_page_results.models import SearchPageResultsModel

from plugins.utils.base_plugin.files import EndpointFile, IntegerEndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def meshfilm() -> Meshfilm:
    return Meshfilm(get_around_client=get_around_client())


# TODO: Validate
class LodpTitleAndPlansPage(IntegerEndpointFile[LodpTitleAndPlansPageModel]):
    """Title information."""

    # TODO: Validate
    @override
    def _endpoint(self) -> LodpTitleAndPlansPageEndpoint:
        return meshfilm().lodp_title_and_plans_page

    # TODO: Validate
    def title_information(self) -> TitleVideo:
        """Return the title information.

        The location of the title information makes it look like it would be information
        for a video."""
        return self.parsed().data.videos[0]


# TODO: Validate
class PreviewModalEpisodeSelector(
    IntegerEndpointFile[PreviewModalEpisodeSelectorModel],
):
    """Season information."""

    # TODO: Validate
    @override
    def _endpoint(self) -> PreviewModalEpisodeSelectorEndpoint:
        return meshfilm().preview_modal_episode_selector

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(int(self.unique_identifier), 500)

    # TODO: Validate
    def seasons(self) -> list[SeasonNode]:
        video = self.parsed().data.videos[0]
        if video.seasons is None:
            msg = "No seasons found for this title."
            raise ValueError(msg)

        return [edge.node for edge in video.seasons.edges]


# TODO: Validate
class PreviewModalEpisodeSelectorSeasonEpisodes(
    IntegerEndpointFile[PreviewModalEpisodeSelectorSeasonEpisodesModel],
):
    """Title information."""

    # TODO: Validate
    @override
    def _endpoint(self) -> PreviewModalEpisodeSelectorSeasonEpisodesEndpoint:
        return meshfilm().preview_modal_episode_selector_season_episodes

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(int(self.unique_identifier), 500)

    # TODO: Validate
    def episodes(self) -> list[EpisodeNode]:
        video = self.parsed().data.videos[0]
        if video.episodes is None:
            msg = "No episodes found for this season."
            raise ValueError(msg)

        return [edge.node for edge in video.episodes.edges]


# TODO: Validate
class SearchPageResults(EndpointFile[SearchPageResultsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SearchPageResultsEndpoint:
        return meshfilm().search_page_results
