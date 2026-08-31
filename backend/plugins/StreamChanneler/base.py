# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.StreamChanneler.watch_history import WatchHistoryMixin
from plugins.utils.base_plugin_v2.base import PluginBase


# TODO: Validate
class StreamChannelerBase(WatchHistoryMixin, PluginBase):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Stream Channeler"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str | None:
        return None

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return ()
