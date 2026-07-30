# TODO: Validate
"""The Roku Channel plugin."""

from __future__ import annotations

from typing import ClassVar, override

from plugins.Roku.handlers import (
    DetailsURLHandler,
    RokuURLHandler,
    WatchURLHandler,
)
from plugins.Roku.helpers import HelperMixin
from plugins.Roku.source import SourceMixin
from plugins.Roku.upsert import UpsertMixin
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

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series or Movie]\n"
            "> `https://therokuchannel.roku.com/details/db1607f1cff2522bb795382bb4b5bcae/fawlty-towers`\n\n"
            "> [!TIP/Episode]\n"
            "> `https://therokuchannel.roku.com/watch/fa455123ce5c5aee995fcf6fd1165e33`\n\n"
        )

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "The Roku Channel"
