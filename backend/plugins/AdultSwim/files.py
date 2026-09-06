# TODO: Validate
"""The files an Adult Swim title is read out of."""

from __future__ import annotations

from functools import cache
from typing import override

from pools_closed import PoolsClosed
from pools_closed.exceptions import ShowNotFoundError
from pools_closed.show import Show as ShowEndpoint
from pools_closed.show.models import ShowModel
from pools_closed.shows import Shows as ShowsEndpoint
from pools_closed.shows.models import ShowsModel
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.utils.base_plugin.files import EndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def pools_closed() -> PoolsClosed:
    return PoolsClosed(get_around_client=get_around_client())


# TODO: Validate
class ShowPage(EndpointFile[ShowModel]):
    @override
    def _endpoint(self) -> ShowEndpoint:
        return pools_closed().show

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class ShowsPage(EndpointFile[ShowsModel]):
    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin) -> None:
        super().__init__(session, plugin, "Shows")

    @override
    def _endpoint(self) -> ShowsEndpoint:
        return pools_closed().shows

    # Required because the endpoint takes no parameters
    @override
    def _download_file(self) -> str:
        return self._endpoint().download()
