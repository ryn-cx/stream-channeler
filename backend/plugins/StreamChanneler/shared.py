# TODO: Validate
"""What the plugin and its initializer both read Stream Channeler by."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from plugins.StreamChanneler.watch_history import StreamChannelerWatchHistoryMixin
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from app.titles.models import Title
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class StreamChannelerShared(StreamChannelerWatchHistoryMixin, BasePlugin):
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

    # StreamChanneler stores no titles of its own. Defined here rather than on
    # the plugin class so the initializer, which shares this base, is concrete
    # too.
    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        msg = "StreamChanneler does not support upserting titles"
        raise NotImplementedError(msg)

    # StreamChanneler does not use files, so these abstract methods are no-ops.
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return []

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        return []
