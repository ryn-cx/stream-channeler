# TODO: Validate
"""What the plugin and its initializer both read Watchmode by."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from plugins.WatchMode.basic_files import BasicFiles
from plugins.WatchMode.utils import title_key

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.media.media_type import TMDBMediaType
    from app.shows.models import Show
    from app.sources.models import Source
    from plugins.utils.base_plugin_v3.files import BaseFile


# TODO: Validate
class WatchModeShared(BasicFiles):
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

    # TODO: Validate
    def source_urls(self, media_type: TMDBMediaType, tmdb_id: int) -> list[str]:
        """Return the web address of every source carrying the TMDB title.

        Ordered as Watchmode listed them and with repeats dropped, since a
        service carrying a title more than one way - included with a
        subscription and also for sale - is listed once per way.
        """
        listing_file = self.title_sources_file(title_key(media_type, tmdb_id))
        # Empty when Watchmode does not carry the title, which is written as a
        # file with no content rather than raised.
        listing = listing_file.parsed_or_none()
        if listing is None:
            return []

        urls: list[str] = []
        for item in listing.root:
            if item.web_url not in urls:
                urls.append(item.web_url)
        return urls

    # Watchmode stores no media of its own, so these abstract methods are no-ops.
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
