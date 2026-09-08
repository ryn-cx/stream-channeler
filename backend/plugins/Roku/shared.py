# TODO: Validate
"""What the plugin, its importers and its initializer all read Roku by."""

from __future__ import annotations

from typing import override

from plugins.Roku.base_files import RokuBaseFiles
from plugins.Roku.utils import search_url


# TODO: Validate
class RokuShared(RokuBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "The Roku Channel"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://therokuchannel.roku.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "therokuchannel.roku.com"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:  # noqa: ARG003 - Roku carries no query in a search address.
        return search_url()
