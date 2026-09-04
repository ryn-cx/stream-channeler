# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.WatchMode.sources import SourcesMixin

if TYPE_CHECKING:
    from app.shows.models import Show
    from app.sources.models import Source


# TODO: Validate
class WatchModeBase(SourcesMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Watchmode"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.watchmode.com/favicon.ico"

    # Watchmode stores no shows of its own. Defined here rather than on the
    # plugin class so the initializer, which shares this base, is concrete too.
    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        msg = "Watchmode stores no shows of its own."
        raise NotImplementedError(msg)
