# TODO: Validate
"""What the plugin, its importers and its initializer all read HBO Max by."""

from __future__ import annotations

from typing import override

from plugins.HBOMax.base_files import HBOMaxBaseFiles
from plugins.HBOMax.utils import search_url


# TODO: Validate
class HBOMaxShared(HBOMaxBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HBO Max"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("HBO Max", "Max")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hbomax.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        return ["play.hbomax.com", "hbomax.com"]

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)
