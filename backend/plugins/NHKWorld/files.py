# TODO: Validate
"""The files NHK World is read out of."""

from __future__ import annotations

import json
from functools import cache
from typing import TYPE_CHECKING, override

from naphki import Naphki
from naphki.exceptions import ProgramNotFoundError
from naphki.video_episodes import VideoEpisodes as VideoEpisodesEndpoint
from naphki.video_episodes.models import VideoEpisodesModel
from naphki.video_program import VideoProgram as VideoProgramEndpoint
from naphki.video_program.models import VideoProgramModel
from naphki.video_programs import VideoPrograms as VideoProgramsEndpoint
from naphki.video_programs.models import VideoProgramsModel

from app.utils import tz_datetime
from plugins.utils.base_plugin.files import (
    PagedEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.constants import INCOMPLETE_STATUS
from plugins.utils.get_around_client import get_around_client

if TYPE_CHECKING:
    from naphki.video_episodes.models import Item
    from naphki.video_programs.models import Item as ProgramItem
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def naphki() -> Naphki:
    return Naphki(get_around_client=get_around_client())


# TODO: Validate
class VideoProgram(SingleArgEndpointFile[VideoProgramModel]):
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
class VideoEpisodes(PagedEndpointFile[VideoEpisodesModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> VideoEpisodesEndpoint:  # type: ignore[override]
        return naphki().video_episodes

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(
            self._endpoint().download_until_datetime(self.unique_identifier),
        )

    # TODO: Validate
    def items(self) -> list[Item]:
        return [item for page in self.parsed() for item in page.items]


# TODO: Validate
class NewVideoEpisodes(PagedEndpointFile[VideoEpisodesModel]):
    # TODO: Validate
    @override
    def _initial_status_after_downloading(self) -> str:
        return INCOMPLETE_STATUS

    # TODO: Validate
    @override
    def _endpoint(self) -> VideoEpisodesEndpoint:  # type: ignore[override]
        return naphki().video_episodes

    # TODO: Consider moving this login into naphki
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # Page 20 at a time (the API default) rather than the 100-entry pages
        # get_all() uses. The initial baseline (to_datetime == now) stops after
        # the first page, and day-to-day there are rarely more than a handful of
        # new episodes, so a single page almost always covers the gap.
        return json.dumps(
            self._endpoint().download_until_datetime(
                end_datetime=tz_datetime.fromisoformat(self.unique_identifier),
            ),
        )

    # TODO: Validate
    def items(self) -> list[Item]:
        return [item for page in self.parsed() for item in page.items]


# TODO: Validate
class VideoPrograms(PagedEndpointFile[VideoProgramsModel]):
    unique_identifier = "VideoPrograms"

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin) -> None:
        super().__init__(session, plugin, self.unique_identifier)

    # TODO: Validate
    @override
    def _endpoint(self) -> VideoProgramsEndpoint:  # type: ignore[override]
        return naphki().video_programs

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(self._endpoint().download_all(unclosed=False))

    # TODO: Validate
    def items(self) -> list[ProgramItem]:
        return [item for page in self.parsed() for item in page.items]
