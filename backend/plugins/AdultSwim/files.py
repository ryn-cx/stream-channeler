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

from plugins.utils.base_plugin.files import NoArgsEndpointFile, SingleArgEndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def pools_closed() -> PoolsClosed:
    return PoolsClosed(get_around_client=get_around_client())


# TODO: Validate
class TitlePage(SingleArgEndpointFile[ShowModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> TitleEndpoint:
        return pools_closed().show

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class TitlesPage(NoArgsEndpointFile[ShowsModel]):
    unique_identifier = "Titles"

    # TODO: Validate
    @override
    def _endpoint(self) -> TitlesEndpoint:
        return pools_closed().shows
