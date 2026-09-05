# TODO: Validate
"""Watchmode plugin.

Looks up which services carry a title and nothing else. Watchmode holds no
listing of its own that a `User` would watch, so this plugin stores no shows,
imports no URLs and is not searched: what it knows is handed to TMDB, which
imports the URLs it gives on whichever scraper accepts them.
"""

from __future__ import annotations

from typing import override

from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer
from plugins.WatchMode.shared import WatchModeShared


# TODO: Validate
class WatchModeInitializer(BasePluginInitializer, WatchModeShared):
    # Watchmode holds no listing of its own, so it has no `Source` to create.
    # TODO: Validate
    @override
    def _create_source_records(self) -> None:
        return


# TODO: Validate
class WatchMode(WatchModeShared, AbstractPlugin, register=False):
    initializer = WatchModeInitializer

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        msg = "No URL is imported from Watchmode."
        raise NotImplementedError(msg)
