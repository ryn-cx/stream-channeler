# TODO: Validate
"""The files Pluto TV is read out of."""

from __future__ import annotations

import json
from datetime import datetime
from functools import cache
from typing import TYPE_CHECKING, override

from notaplanet import NotAPlanet
from notaplanet.browse_nav import BrowseNav as BrowseNavEndpoint
from notaplanet.browse_nav.models import BrowseNavModel
from notaplanet.carousel import Carousel as CarouselEndpoint
from notaplanet.carousel.models import CarouselModel
from notaplanet.exceptions import NotAPlanetError, SeriesNotFoundError
from notaplanet.hub import Hub as HubEndpoint
from notaplanet.hub.models import HubModel
from notaplanet.items import Items as ItemsEndpoint
from notaplanet.items.models import ItemsModel
from notaplanet.seasons import Seasons as SeasonsEndpoint
from notaplanet.seasons.models import SeasonsModel

from app.utils import tz_datetime
from plugins.utils.base_plugin.files import (
    APIClientFile,
    MultipleArgEndpointFile,
    NoArgsEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.constants import COMPLETE_CATALOG_UPDATE_INTERVAL
from plugins.utils.proxy_client import proxy_client

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def notaplanet() -> NotAPlanet:
    return NotAPlanet(get_around_client=proxy_client())


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
class BrowseNavFile(NoArgsEndpointFile[BrowseNavModel]):
    unique_identifier = "browse_nav"

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + COMPLETE_CATALOG_UPDATE_INTERVAL

    # TODO: Validate
    @override
    def _endpoint(self) -> BrowseNavEndpoint:
        return notaplanet().browse_nav


# TODO: Validate
class HubFile(SingleArgEndpointFile[HubModel]):
    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + COMPLETE_CATALOG_UPDATE_INTERVAL

    # TODO: Validate
    @override
    def _endpoint(self) -> HubEndpoint:
        return notaplanet().hub


# TODO: Validate
class CarouselFile(MultipleArgEndpointFile[CarouselModel]):
    # TODO: Validate
    def __init__(  # noqa: PLR0913
        self,
        session: Session,
        plugin: Plugin,
        hub_slug: str,
        carousel_id: str,
        token: str,
        model: str,
    ) -> None:
        self.hub_slug = hub_slug
        self.carousel_id = carousel_id
        self.token = token
        self.model = model
        super().__init__(session, plugin, f"{hub_slug}/{carousel_id}")

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + COMPLETE_CATALOG_UPDATE_INTERVAL

    # TODO: Validate
    @override
    def _endpoint(self) -> CarouselEndpoint:
        return notaplanet().carousel

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.token, model=self.model)


# TODO: Validate
class CatalogItemsFile(APIClientFile[list[ItemsModel]]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        item_keys: tuple[str, ...],
    ) -> None:
        self.item_keys = item_keys
        super().__init__(session, plugin, "catalog")

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + COMPLETE_CATALOG_UPDATE_INTERVAL

    # TODO: Validate
    @override
    def _endpoint(self) -> ItemsEndpoint:
        return notaplanet().items

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(self._endpoint().download_all(self.item_keys))

    # TODO: Validate
    @override
    def _parse(self, content: str) -> list[ItemsModel]:
        pages: list[str] = json.loads(content)
        return [self._endpoint().load(page, self.log_id()) for page in pages]
