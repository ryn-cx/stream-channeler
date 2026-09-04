# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.StreamChanneler.watch_history import WatchHistoryMixin
from plugins.utils.base_plugin_v2.base import BasePlugin

if TYPE_CHECKING:
    from app.shows.models import Show
    from app.sources.models import Source


# TODO: Validate
class StreamChannelerBase(WatchHistoryMixin, BasePlugin):
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
