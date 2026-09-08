# TODO: Validate
"""The files an Adult Swim title is read out of."""

from __future__ import annotations

from functools import cache
from typing import override

from pools_closed import PoolsClosed
from pools_closed.exceptions import ShowNotFoundError
from pools_closed.show import Show as TitleEndpoint
from pools_closed.show.models import ShowModel
from pools_closed.shows import Shows as TitlesEndpoint
from pools_closed.shows.models import ShowsModel
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.utils.base_plugin.files import INCOMPLETE_STATUS, EndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def pools_closed() -> PoolsClosed:
    return PoolsClosed(get_around_client=get_around_client())


# TODO: Validate
class TitlePage(EndpointFile[ShowModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> TitleEndpoint:
        return pools_closed().show

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class TitlesPage(EndpointFile[ShowsModel]):
    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin) -> None:
        super().__init__(session, plugin, "Titles")

    # TODO: Validate
    @override
    def _endpoint(self) -> TitlesEndpoint:
        return pools_closed().shows

    # Required because the endpoint takes no parameters
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download()

    # TODO: Validate
    @override
    def _initial_status_after_downloading(self) -> str:
        return INCOMPLETE_STATUS
