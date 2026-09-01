# TODO: Validate
"""Watchmode plugin.

Looks up which services carry a title and nothing else. Watchmode holds no
listing of its own that a `User` would watch, so this plugin stores no shows,
imports no URLs and is not searched: what it knows is handed to TMDB, which
imports the URLs it gives on whichever scraper accepts them.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, override

from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.WatchMode.base import WatchModeBase
from plugins.WatchMode.initialize import WatchModeInitializer

if TYPE_CHECKING:
    from plugins.utils.base_plugin_v2.files import BaseFile


# TODO: Validate
class WatchMode(WatchModeBase, AbstractPlugin, register=True):
    """Watchmode plugin."""

    initializer = WatchModeInitializer

    # Watchmode stores no media of its own, so these abstract methods are no-ops
    # or raise. Nothing is meant to reach the ones that raise; they are here to
    # let the class be instantiated for the lookup that is its whole purpose.
    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        msg = "No URL is imported from Watchmode."
        raise NotImplementedError(msg)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return []

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        return []
