# TODO: Validate
"""What the plugin and its initializer both read Stream Channeler by."""

from __future__ import annotations

from typing import override

from plugins.utils.base_plugin.core import BasePluginCore


# TODO: Validate
class StreamChannelerShared(BasePluginCore):
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
    def _domains(cls) -> list[str]:
        return []

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return ()
