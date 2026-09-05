# TODO: Validate
"""What the plugin and its initializer both read Stream Channeler by."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from plugins.StreamChanneler.watch_history import WatchHistoryMixin
from plugins.utils.base_plugin_v3.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.shows.models import Show
    from app.sources.models import Source
    from plugins.utils.base_plugin_v3.files import BaseFile


# TODO: Validate
class StreamChannelerShared(WatchHistoryMixin, BasePlugin):
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

    # StreamChanneler stores no shows of its own. Defined here rather than on
    # the plugin class so the initializer, which shares this base, is concrete
    # too.
    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        msg = "StreamChanneler does not support upserting shows"
        raise NotImplementedError(msg)

    # StreamChanneler does not use files, so these abstract methods are no-ops.
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
