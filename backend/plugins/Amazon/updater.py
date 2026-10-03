# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Amazon.shared import AmazonShared
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class AmazonUpdater(AmazonShared, BasePluginUpdater):
    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return []

    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (
            "Amazon Prime",
            "Free on Amazon",
            "Purchase on Amazon",
            "Unavailable on Amazon",
        )

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:
        detail_file = self.detail_file(title.key)
        return detail_file.other_title_urls_on_this_page("Customers also watched")
