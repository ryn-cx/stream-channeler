# TODO: Validate
"""What the plugin, its importers and its initializer all read Disney+ by."""

from __future__ import annotations

from typing import override

from plugins.DisneyPlus.base_files import DisneyPlusBaseFiles


# TODO: Validate
class DisneyPlusShared(DisneyPlusBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Disney+"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.disneyplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "disneyplus.com"
