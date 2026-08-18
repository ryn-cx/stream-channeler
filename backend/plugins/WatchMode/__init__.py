# TODO: Validate
"""Watchmode plugin.

Looks up which services carry a title and nothing else. Watchmode holds no
listing of its own that a `User` would watch, so this plugin stores no shows,
imports no URLs and is not searched: what it knows is handed to TMDB, which
imports the URLs it gives on whichever scraper accepts them.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, override

from app.shows.models import Show
from app.sources.models import Source
from plugins.utils.base_plugin.files import BaseFile
from plugins.WatchMode.sources import SourcesMixin


# TODO: Validate
class WatchMode(SourcesMixin, register=True):
    """Watchmode plugin."""

    _VERSION = "0.0.1"
    FAVICON_URL = "https://www.watchmode.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Watchmode"

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
    def initialize_sources(self) -> None:
        return

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> Show:
        msg = "Watchmode stores no shows of its own."
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
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        return []

    # TODO: Validate
    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        return []
