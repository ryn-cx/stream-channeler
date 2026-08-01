# TODO: Validate
"""The Roku Channel plugin."""

from __future__ import annotations

from typing import ClassVar, override

from plugins.Roku.helpers import HelperMixin
from plugins.Roku.source import SourceMixin
from plugins.Roku.upsert import UpsertMixin
from plugins.Roku.url_handlers import (
    DetailsURLHandler,
    RokuURLHandler,
    WatchURLHandler,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Roku(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    URLHandlerPlugin[RokuURLHandler],
    register=True,
):
    """The Roku Channel plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[RokuURLHandler], ...]] = (
        DetailsURLHandler,
        WatchURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("The Roku Channel",)
    FAVICON_URL = "https://therokuchannel.roku.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "therokuchannel.roku.com"

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "The Roku Channel"
