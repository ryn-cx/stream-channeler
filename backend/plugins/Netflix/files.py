# TODO: Validate
from __future__ import annotations

from functools import cache
from typing import override

from meshfilm import Meshfilm
from meshfilm.detail_modal import DetailModal as DetailModalEndpoint
from meshfilm.detail_modal.models import DetailModalModel
from meshfilm.exceptions import TitleNotFoundError
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

from plugins.utils.base_plugin.files import (
    IntegerArgEndpointFile,
)
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def meshfilm() -> Meshfilm:
    # Netflix needs to use the proxy because get-around sometimes routes to an IP in
    # another country which causes incorrect results.
    return Meshfilm(get_around_client=get_around_client(proxy=True))


# TODO: Validate
class DetailModal(IntegerArgEndpointFile[DetailModalModel]):
    """Title information."""

    # TODO: Validate
    @override
    def _endpoint(self) -> DetailModalEndpoint:
        return meshfilm().detail_modal

    # Occurs if the user tries to add an invalid URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, TitleNotFoundError)


# TODO: Validate
class PreviewModalEpisodeSelector(
    IntegerArgEndpointFile[PreviewModalEpisodeSelectorModel],
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
        return [edge.node for edge in self.parsed().seasons.edges]


# TODO: Validate
class PreviewModalEpisodeSelectorSeasonEpisodes(
    IntegerArgEndpointFile[PreviewModalEpisodeSelectorSeasonEpisodesModel],
):
    """Season Episodes information."""

    # TODO: Validate
    @override
    def _endpoint(self) -> PreviewModalEpisodeSelectorSeasonEpisodesEndpoint:
        return meshfilm().preview_modal_episode_selector_season_episodes

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(int(self.unique_identifier), count=500)

    # TODO: Validate
    def episodes(self) -> list[EpisodeNode]:
        return [edge.node for edge in self.parsed().episodes.edges]
