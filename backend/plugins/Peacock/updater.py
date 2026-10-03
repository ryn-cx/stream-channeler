# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from pigeon.show import SHOW_TYPE

from plugins.Peacock.files import CollectionFile
from plugins.Peacock.shared import PeacockShared
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pigeon.collection.models import CollectionModel
    from pigeon.collection.models import Datum as CollectionItem


# TODO: Validate
class PeacockUpdater(PeacockShared, BasePluginUpdater):
    # TODO: Validate
    def collection_file(self, slug: str) -> CollectionFile:
        return self._cached_file(CollectionFile, slug)

    # TODO: Validate
    @override
    def _plugin_files(self) -> Sequence[CollectionFile]:
        return [
            self.collection_file("/tv/tv-shows-a-z"),
            self.collection_file("/movies/a-z"),
        ]

    # TODO: Validate
    @override
    def _title_keys_from_plugin_files(self) -> list[str]:
        return [self.collection_title_key(item) for item in self._plugin_file_items()]

    # TODO: Validate
    @override
    def _import_plugin_files(self) -> None:
        super()._import_plugin_files()
        for collection_file in self._plugin_files():
            self._mark_titles_with_changed_listings(
                None,
                {
                    self.collection_title_key(item): [
                        item.attributes.available_season_count,
                        item.attributes.available_episode_count,
                    ]
                    for item in self.collection_items(collection_file.parsed())
                    if item.type == SHOW_TYPE
                },
                collection_file.record_data_timestamp,
            )

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return [
            self.asset_url(item.attributes.slug) for item in self._plugin_file_items()
        ]

    # TODO: Validate
    def _plugin_file_items(self) -> list[CollectionItem]:
        self._download_if_outdated(self._plugin_files())
        return [
            item
            for collection_file in self._plugin_files()
            for item in self.collection_items(collection_file.parsed())
        ]

    # TODO: Validate
    @staticmethod
    def required_value[ValueT](value: ValueT | None, description: str) -> ValueT:
        """Return `value`, raising when the API left it out."""
        if value is None:
            msg = f"The node has no {description}."
            raise ValueError(msg)
        return value

    # TODO: Validate
    @staticmethod
    def collection_items(collection: CollectionModel) -> list[CollectionItem]:
        return collection.relationships.items.data

    # TODO: Validate
    @classmethod
    def collection_title_key(cls, item: CollectionItem) -> str:
        # A handful of movies carry a `providerSeriesId` that is not an id at all, so
        # the node's own type is what says which of the two ids keys it.
        if item.type == SHOW_TYPE:
            return cls.required_value(item.attributes.provider_series_id, "series id")
        return str(
            cls.required_value(item.attributes.provider_variant_id, "variant id"),
        )
