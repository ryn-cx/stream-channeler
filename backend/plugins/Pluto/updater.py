# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.utils.strict_re import strict_search
from plugins.Pluto.constants import CAROUSEL_HREF_REGEX
from plugins.Pluto.files import (
    BrowseNavFile,
    CarouselFile,
    CatalogItemsFile,
    HubFile,
)
from plugins.Pluto.shared import PlutoShared
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from notaplanet.browse_nav.models import MovieBrowseNavItem, ShowBrowseNavItem
    from notaplanet.carousel.models import Datum as CarouselItem
    from notaplanet.hub.models import HubCarousel
    from notaplanet.items.models import ItemsModelItem


# TODO: Validate
class PlutoUpdater(PlutoShared, BasePluginUpdater):
    # TODO: Validate
    @staticmethod
    def carousel_item_key(carousel_item: CarouselItem) -> str:
        return strict_search(CAROUSEL_HREF_REGEX, carousel_item.href).group("item_key")

    # TODO: Validate
    @classmethod
    def item_url(cls, item: ItemsModelItem) -> str:
        if item.type == "series":
            return cls.series_url(item.field_id)
        if item.type == "movie":
            return cls.movie_url(item.field_id)
        msg = f"Unknown item type {item.type!r} for {item.field_id}"
        raise ValueError(msg)

    # TODO: Validate
    @staticmethod
    def media_type_channel_key(item: ItemsModelItem) -> str:
        return "Series" if item.type == "series" else "Movies"

    # TODO: Validate
    def browse_nav_file(self) -> BrowseNavFile:
        return self._cached_file(BrowseNavFile)

    # TODO: Validate
    def hub_file(self, hub_slug: str) -> HubFile:
        return self._cached_file(HubFile, hub_slug)

    # TODO: Validate
    def carousel_file(self, hub_slug: str, carousel: HubCarousel) -> CarouselFile:
        return self._cached_file(
            CarouselFile,
            hub_slug,
            carousel.carousel_id,
            carousel.token,
            carousel.model,
        )

    # TODO: Validate
    def catalog_items_file(self) -> CatalogItemsFile:
        item_keys = {
            self.carousel_item_key(carousel_item): None
            for hub in self.hubs()
            for carousel_file in self.hub_carousel_files(hub.slug)
            for carousel_item in carousel_file.parsed().result.data
        }
        return self._cached_file(CatalogItemsFile, tuple(item_keys))

    # TODO: Validate
    def hubs(self) -> list[ShowBrowseNavItem | MovieBrowseNavItem]:
        self.browse_nav_file().download_if_outdated()
        global_menu = self.browse_nav_file().parsed().global_menu
        return [*global_menu.show_browse_nav, *global_menu.movie_browse_nav]

    # TODO: Validate
    def hub_carousel_files(self, hub_slug: str) -> list[CarouselFile]:
        self.hub_file(hub_slug).download_if_outdated()
        carousel_files = [
            self.carousel_file(hub_slug, carousel)
            for carousel in self.hub_file(hub_slug).parsed().hub_carousels
        ]
        self._download_if_outdated(carousel_files)
        return carousel_files

    # TODO: Validate
    @override
    def _plugin_files(
        self,
    ) -> Sequence[BrowseNavFile | HubFile | CarouselFile | CatalogItemsFile]:
        hub_slugs = [hub.slug for hub in self.hubs()]
        return [
            self.browse_nav_file(),
            *(self.hub_file(hub_slug) for hub_slug in hub_slugs),
            *(
                carousel_file
                for hub_slug in hub_slugs
                for carousel_file in self.hub_carousel_files(hub_slug)
            ),
            self.catalog_items_file(),
        ]

    # TODO: Validate
    def _catalog_items(self) -> list[ItemsModelItem]:
        self._download_if_outdated(self._plugin_files())
        return [
            item for page in self.catalog_items_file().parsed() for item in page.root
        ]

    # TODO: Validate
    @override
    def _title_keys_from_plugin_files(self) -> set[str]:
        return {item.field_id for item in self._catalog_items()}

    # TODO: Validate
    @override
    def _import_plugin_files(self) -> None:
        super()._import_plugin_files()
        self._mark_titles_with_changed_listings(
            None,
            {
                item.field_id: item.seasons_numbers
                for item in self._catalog_items()
                if item.type == "series"
            },
            self.catalog_items_file().record_data_timestamp,
        )

    # TODO: Validate
    def _hub_items(
        self,
        hub_slug: str,
        items_by_key: dict[str, ItemsModelItem],
    ) -> list[ItemsModelItem]:
        return [
            item
            for carousel_file in self.hub_carousel_files(hub_slug)
            for carousel_item in carousel_file.parsed().result.data
            if (item := items_by_key.get(self.carousel_item_key(carousel_item)))
        ]

    # TODO: Validate
    def _channel_urls(
        self,
    ) -> tuple[dict[str, list[str]], dict[str, tuple[list[str], datetime]]]:
        items_by_key = {
            item.slug if item.type == "series" else item.field_id: item
            for item in self._catalog_items()
        }
        urls_by_channel_key: dict[str, dict[str, None]] = {}
        list_urls_by_channel_key: dict[str, dict[str, None]] = {}
        data_timestamps: dict[str, datetime] = {}
        for hub in self.hubs():
            is_list = not hub.slug.endswith(("-featured", "-all-shows", "-all-movies"))
            if is_list:
                data_timestamp = min(
                    hub_data_file.record_data_timestamp
                    for hub_data_file in [
                        self.hub_file(hub.slug),
                        *self.hub_carousel_files(hub.slug),
                        self.catalog_items_file(),
                    ]
                )
                data_timestamps[hub.label] = min(
                    data_timestamps.get(hub.label, data_timestamp),
                    data_timestamp,
                )
                list_urls_by_channel_key.setdefault(hub.label, {})
            for item in self._hub_items(hub.slug, items_by_key):
                title_url = self.item_url(item)
                for channel_key in ["All Titles", self.media_type_channel_key(item)]:
                    urls_by_channel_key.setdefault(channel_key, {})[title_url] = None
                if is_list:
                    list_urls_by_channel_key[hub.label][title_url] = None
        return (
            {
                channel_key: list(urls)
                for channel_key, urls in urls_by_channel_key.items()
            },
            {
                channel_key: (list(urls), data_timestamps[channel_key])
                for channel_key, urls in list_urls_by_channel_key.items()
                if urls
            },
        )

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        urls_by_channel_key, _ = self._channel_urls()
        return urls_by_channel_key.get("All Titles", [])

    # TODO: Validate
    @override
    def create_initial_channel_records(self) -> None:
        urls_by_channel_key, list_channels = self._channel_urls()
        for channel_key, urls in urls_by_channel_key.items():
            self.add_new_urls_to_channel(channel_key, urls)
        for channel_key, (urls, data_timestamp) in list_channels.items():
            self.replace_list_channels({channel_key: urls}, data_timestamp)
