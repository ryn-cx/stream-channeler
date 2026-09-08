# TODO: Validate
"""The files NHK World is read out of."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, override

from naphki import Naphki
from naphki.exceptions import ProgramNotFoundError
from naphki.shows_search import ShowsSearch as TitlesSearchEndpoint
from naphki.shows_search.models import ShowsSearchModel
from naphki.video_episodes import VideoEpisodes as VideoEpisodesEndpoint
from naphki.video_episodes.models import VideoEpisodesModel
from naphki.video_program import VideoProgram as VideoProgramEndpoint
from naphki.video_program.models import VideoProgramModel

from plugins.utils.base_plugin.files import EndpointFile
from plugins.utils.get_around_client import get_around_client

if TYPE_CHECKING:
    from naphki.video_episodes.models import Item
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def naphki() -> Naphki:
    return Naphki(get_around_client=get_around_client())


# TODO: Validate
class VideoProgram(EndpointFile[VideoProgramModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> VideoProgramEndpoint:
        return naphki().video_program

    # Occurs when a user puts in an invalid URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ProgramNotFoundError)


# TODO: Validate
class VideoEpisodes(EndpointFile[VideoEpisodesModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> VideoEpisodesEndpoint:
        return naphki().video_episodes

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download_merged_until_datetime(self.unique_identifier)

    # TODO: Validate
    def items(self) -> list[Item]:
        return self.parsed().items


# TODO: Validate
class NewVideoEpisodes(EndpointFile[VideoEpisodesModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> VideoEpisodesEndpoint:
        return naphki().video_episodes

    # TODO: Consider moving this login into naphki
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # Page 20 at a time (the API default) rather than the 100-entry pages
        # get_all() uses. The initial baseline (to_datetime == now) stops after
        # the first page, and day-to-day there are rarely more than a handful of
        # new episodes, so a single page almost always covers the gap.
        return self._endpoint().download_merged_until_datetime(
            end_datetime=self.identifier_datetime(),
        )

    # TODO: Validate
    def items(self) -> list[Item]:
        return self.parsed().items


# TODO: Validate
class TitlesSearch(EndpointFile[ShowsSearchModel]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        offset: int,
    ) -> None:
        self.query = query
        self.offset = offset
        super().__init__(session, plugin, f"{query}/{offset}")

    # TODO: Validate
    @override
    def _endpoint(self) -> TitlesSearchEndpoint:
        return naphki().shows_search

    # `size` keeps its default so a page request looks exactly like the one the
    # website makes.
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, from_=self.offset)
