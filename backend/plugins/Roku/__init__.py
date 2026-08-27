# TODO: Validate
"""The Roku Channel plugin."""

from __future__ import annotations

from typing import override

from plugins.Roku.media_info import MediaInfoMixin
from plugins.Roku.source import SourceMixin
from plugins.Roku.upsert import UpsertMixin
from plugins.Roku.url_handlers import (
    DetailsURLHandler,
    RokuURLHandler,
    WatchURLHandler,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class Roku(
    UpsertMixin,
    MediaInfoMixin,
    SourceMixin,
    URLHandlerPlugin[RokuURLHandler],
    register=True,
):
    """The Roku Channel plugin."""

    # TODO: Validate
    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[RokuURLHandler], ...]:
        return (
            DetailsURLHandler,
            WatchURLHandler,
        )

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("The Roku Channel",)

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://therokuchannel.roku.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "therokuchannel.roku.com"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "The Roku Channel"
