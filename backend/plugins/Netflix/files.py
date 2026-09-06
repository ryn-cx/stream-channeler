# TODO: Validate
"""The files a Netflix title is read out of.

Netflix answers with the whole of a title at once, so a show, its seasons and
their episodes all come out of the one file the title is downloaded as.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import cache
from typing import override

from meshfilm import Meshfilm
from meshfilm.lodp_title_and_plans_page import LodpTitleAndPlansPage
from meshfilm.lodp_title_and_plans_page.models import LodpTitleAndPlansPageModel
from meshfilm.preview_modal_episode_selector import PreviewModalEpisodeSelector
from meshfilm.preview_modal_episode_selector.models import (
    PreviewModalEpisodeSelectorModel,
)
from meshfilm.preview_modal_episode_selector_season_episodes import (
    PreviewModalEpisodeSelectorSeasonEpisodes,
)
from meshfilm.preview_modal_episode_selector_season_episodes.models import (
    PreviewModalEpisodeSelectorSeasonEpisodesModel,
)
from meshfilm.search_page_results import SearchPageResults
from meshfilm.search_page_results.models import SearchPageResultsModel
from sqlmodel import Session

from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.utils.base_plugin.files import EndpointFile, IntegerEndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def meshfilm() -> Meshfilm:
    return Meshfilm(get_around_client=get_around_client())


# TODO: Validate
class Title(IntegerEndpointFile[LodpTitleAndPlansPageModel]):
    @override
    def _endpoint(self) -> LodpTitleAndPlansPage:
        return meshfilm().lodp_title_and_plans_page


# TODO: Validate
class Seasons(IntegerEndpointFile[PreviewModalEpisodeSelectorModel]):
    @override
    def _endpoint(self) -> PreviewModalEpisodeSelector:
        return meshfilm().preview_modal_episode_selector

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(int(self.unique_identifier), 500)


# TODO: Validate
class SeasonEpisodes(
    IntegerEndpointFile[PreviewModalEpisodeSelectorSeasonEpisodesModel],
):
    @override
    def _endpoint(self) -> PreviewModalEpisodeSelectorSeasonEpisodes:
        return meshfilm().preview_modal_episode_selector_season_episodes

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(int(self.unique_identifier), 500)


# TODO: Validate
class Search(EndpointFile[SearchPageResultsModel]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        cursor: str,
    ) -> None:
        self.query = query
        self.cursor = cursor
        super().__init__(session, plugin, f"{query}/{cursor}")

    @override
    def _endpoint(self) -> SearchPageResults:
        return meshfilm().search_page_results

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, self.cursor or None)

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)
