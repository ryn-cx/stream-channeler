# TODO: Validate
"""Amazon Prime Video plugin."""

from __future__ import annotations

from typing import ClassVar, override

from plugins.Amazon.handlers import AmazonURLHandler, DetailURLHandler
from plugins.Amazon.helpers import HelperMixin
from plugins.Amazon.source import SourceMixin
from plugins.Amazon.upsert import UpsertMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Amazon(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    URLHandlerPlugin[AmazonURLHandler],
    register=True,
):
    """Amazon Prime Video plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[AmazonURLHandler], ...]] = (DetailURLHandler,)
    TMDB_PROVIDER_NAMES = ("Amazon Prime Video", "Amazon Video", "Prime Video")
    FAVICON_URL = "https://www.amazon.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "amazon.com"

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Amazon Prime Video"
