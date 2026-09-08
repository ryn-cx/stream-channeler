# TODO: Validate
"""What the plugin, its importers and its initializer all read Tubi by."""

from __future__ import annotations

from typing import override

from plugins.Tubi.base_files import TubiBaseFiles
from plugins.Tubi.utils import search_url


# TODO: Validate
class TubiShared(TubiBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Tubi"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Tubi TV", "Tubi")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://tubitv.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)
