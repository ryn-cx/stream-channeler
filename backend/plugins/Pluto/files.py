# TODO: Validate
"""The files Pluto TV is read out of."""

from __future__ import annotations

from functools import cache
from typing import override

from notaplanet import NotAPlanet
from notaplanet.exceptions import NotAPlanetError, SeriesNotFoundError
from notaplanet.items import Items as ItemsEndpoint
from notaplanet.items.models import ItemsModel
from notaplanet.seasons import Seasons as SeasonsEndpoint
from notaplanet.seasons.models import SeasonsModel

from plugins.utils.base_plugin.files import (
    SingleArgEndpointFile,
    MultipleArgEndpointFile,
)
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def notaplanet() -> NotAPlanet:
    return NotAPlanet(get_around_client=get_around_client())


# TODO: Validate
class ItemNotFoundError(NotAPlanetError):
    """Raised when nothing is filed under the requested item id."""

    # TODO: Validate
    def __init__(self, item_id: str) -> None:
        """Initialize with the item id that nothing is filed under."""
        self.item_id = item_id
        super().__init__(f"No item is filed under {item_id!r}")


# TODO: Validate
class ItemsFile(MultipleArgEndpointFile[ItemsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ItemsEndpoint:
        return notaplanet().items

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        data = self._endpoint().download([self.unique_identifier])
        if not self._endpoint().load(data, self.log_id()).root:
            raise ItemNotFoundError(self.unique_identifier)
        return data

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ItemNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_status(self) -> str:
        """Return what is written down in place of a title that does not exist."""
        return f"Invalid item_id {self.unique_identifier}"


# TODO: Validate
class SeasonsFile(SingleArgEndpointFile[SeasonsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SeasonsEndpoint:
        return notaplanet().seasons

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_status(self) -> str:
        """Return what is written down in place of a series that does not exist."""
        return f"Invalid series_id {self.unique_identifier}"
