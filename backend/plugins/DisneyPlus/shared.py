# TODO: Validate
"""What the plugin, its importers and its initializer all read Disney+ by."""

from __future__ import annotations

from typing import override

from plugins.DisneyPlus.base_files import DisneyPlusBaseFiles
from plugins.DisneyPlus.utils import search_url

# https://www.disneyplus.com/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
# https://www.disneyplus.com/en-gb/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
# The optional locale segment, e.g. /en-gb or /de.
ENTITY_URL_REGEX = (
    r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?\/browse\/entity-"
    r"(?P<entity_key>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"(?:\/|$)"
)


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

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:  # noqa: ARG003 - Disney+ carries no query in a search address.
        return search_url()
