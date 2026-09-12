# TODO: Validate
"""What the plugin, its importers and its initializer all read YouTube by."""

from __future__ import annotations

from typing import override

from plugins.YouTube.base_files import YouTubeBaseFiles
from plugins.YouTube.constants import (
    LINKS_SOURCE_KEY,
    LONG_DOMAIN,
    MUSIC_SOURCE_KEY,
    SHORT_DOMAIN,
)

# from plugins.YouTube.watch_history import YouTubeWatchHistoryMixin


# TODO: Validate
class YouTubeShared(YouTubeBaseFiles):
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
    def _domains(cls) -> list[str]:
        return [LONG_DOMAIN, SHORT_DOMAIN]

    # TODO: Validate
    @classmethod
    @override
    def _link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (
            cls.plugin_name(),
            # FREE_SOURCE_KEY,
            # PAID_SOURCE_KEY,
            LINKS_SOURCE_KEY,
            MUSIC_SOURCE_KEY,
        )
