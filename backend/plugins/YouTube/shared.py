# TODO: Validate
"""What the plugin, its importers and its initializer all read YouTube by."""

from __future__ import annotations

from typing import override

from app.sources.models import Source
from plugins.YouTube.base_files import YouTubeBaseFiles
from plugins.YouTube.constants import (
    FREE_SOURCE_KEY,
    LINKS_SOURCE_KEY,
    LONG_DOMAIN,
    PAID_SOURCE_KEY,
    SHORT_DOMAIN,
)
from plugins.YouTube.utils import (
    search_url,
)
from plugins.YouTube.watch_history import YouTubeWatchHistoryMixin


# TODO: Validate
class YouTubeShared(YouTubeWatchHistoryMixin, YouTubeBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "YouTube"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return (
            "https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png"
        )

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        return [LONG_DOMAIN, SHORT_DOMAIN]

    # TODO: Validate
    @classmethod
    @override
    def link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_name(), FREE_SOURCE_KEY, PAID_SOURCE_KEY, LINKS_SOURCE_KEY)

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        existing_source = Source.get(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=self._existing_data_timestamp_or_now(existing_source),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source
