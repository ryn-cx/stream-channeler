# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Amazon.shared import AmazonShared
from plugins.utils.base_plugin.linker import BasePluginLinker


# TODO: Validate
class AmazonLinker(AmazonShared, BasePluginLinker):
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        # This is just the names that do not fall under the "XXX Amazon Channel" format,
        # those names are checked in matches_tmdb_provider.
        return (
            "Amazon Prime Video",
            "Amazon Prime Video Free with Ads",
            "Amazon Prime Video with Ads",
            "Amazon Video",
        )

    @classmethod
    @override
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        if super().matches_tmdb_provider(provider_name):
            return True
        return provider_name.casefold().endswith("amazon channel")
