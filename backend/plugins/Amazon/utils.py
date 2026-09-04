# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

from typing import override
from urllib.parse import quote_plus

from plugins.utils.base_plugin_v2.base import BasePlugin


# TODO: Validate
class UtilsMixin(BasePlugin):
    """The URLs of a title and the key it is stored under."""

    # TODO: Validate
    @classmethod
    def _detail_url(cls, compact_key: str) -> str:
        return cls.build_url(f"detail/{compact_key}")

    # TODO: Validate
    @override
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return cls.build_url(f"region/na/search?phrase={quote_plus(query)}")


