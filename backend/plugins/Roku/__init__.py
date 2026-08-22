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
    register=False,
):
    """The Roku Channel plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (
        DetailsURLHandler,
        WatchURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("The Roku Channel",)
    FAVICON_URL = "https://therokuchannel.roku.com/favicon.ico"

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
