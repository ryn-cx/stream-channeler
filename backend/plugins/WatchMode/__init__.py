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
from plugins.WatchMode.base import WatchModeBase
from plugins.WatchMode.initialize import WatchModeInitializer


# TODO: Validate
class WatchMode(WatchModeBase, AbstractPlugin, register=False):
    """Watchmode plugin."""

    initializer = WatchModeInitializer

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        msg = "No URL is imported from Watchmode."
        raise NotImplementedError(msg)
