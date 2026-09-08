# TODO: Validate
"""What the plugin, its importers and its initializer all read Pluto TV by."""

from __future__ import annotations

from typing import override

from plugins.Pluto.base_files import PlutoBaseFiles
from plugins.Pluto.utils import search_url


# TODO: Validate
class PlutoShared(PlutoBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Pluto TV"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://pluto.tv/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "pluto.tv"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)
