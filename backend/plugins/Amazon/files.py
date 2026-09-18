from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, override

from deforestation import Deforestation
from deforestation.detail import Detail as DetailEndpoint
from deforestation.detail.models import ParsedDetailModel
from deforestation.detail_widgets import DetailWidgets as DetailWidgetsEndpoint
from deforestation.detail_widgets.models import ParsedDetailWidgetsModel
from deforestation.exceptions import TitleNotFoundError

from plugins.utils.base_plugin.files import (
    MultipleArgEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.get_around_client import get_around_client

if TYPE_CHECKING:
    from deforestation.detail_widgets.models import Episode as WidgetEpisode
    from sqlmodel import Session

    from app.plugins.models import Plugin


@cache
def deforestation() -> Deforestation:
    return Deforestation(get_around_client=get_around_client())


class Detail(SingleArgEndpointFile[ParsedDetailModel]):
    """Contains title details."""
    @override
    def _endpoint(self) -> DetailEndpoint:
        return deforestation().detail

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        # Occurs when a user puts in an invalid URL.
        return isinstance(error, TitleNotFoundError)

    def other_title_urls_on_this_page(
        self,
        container_title: str | None = None,
    ) -> set[str]:
        return {
            title.url
            for container in self.parsed().containers
            if container_title is None or container.title == container_title
            for title in container.titles
        }


class DetailWidgets(MultipleArgEndpointFile[ParsedDetailWidgetsModel]):
    """Contains the episode list for a title."""

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        season_key: str,
        page_index: int,
    ) -> None:
        self.season_key = season_key
        self.page_index = page_index
        super().__init__(session, plugin, f"{season_key}/{page_index}")

    @override
    def _endpoint(self) -> DetailWidgetsEndpoint:
        return deforestation().detail_widgets

    @override
    # TODO: Downloads may fail in the future due to the token expiring. Watch for
    # download errors in the logs.
    def _download_file(self) -> str:
        detail = Detail(self._session, self._plugin, self.season_key)
        detail.download_if_outdated()
        pages = detail.parsed().episode_pages
        return self._endpoint().download(self.season_key, pages[self.page_index].token)

    def episodes(self) -> list[WidgetEpisode]:
        return [episode for episode in self.parsed().episodes if episode.is_available]
