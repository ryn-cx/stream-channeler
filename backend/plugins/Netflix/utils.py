# TODO: Validate
"""The URLs a Netflix title and its episodes are watched at."""

from __future__ import annotations

from typing import override
from urllib.parse import quote_plus

from plugins.utils.base_plugin_v2.base import PluginBase


# TODO: Validate
class UtilsMixin(PluginBase):
    """The URLs of a title and of the episodes under it."""

    # TODO: Validate
    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"title/{show_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    # TODO: Validate
    @classmethod
    @override
    def manual_search(cls, query: str) -> str:
        return cls.build_url(f"search?q={quote_plus(query)}")
