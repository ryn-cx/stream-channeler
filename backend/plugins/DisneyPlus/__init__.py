# TODO: Validate
"""Disney+ plugin."""

from __future__ import annotations

from typing import override

from plugins.DisneyPlus.helpers import HelperMixin
from plugins.DisneyPlus.source import SourceMixin
from plugins.DisneyPlus.upsert import UpsertMixin
from plugins.DisneyPlus.url_handlers import DisneyPlusURLHandler, EntityURLHandler
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class DisneyPlus(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    URLHandlerPlugin[DisneyPlusURLHandler],
    register=True,
):
    """Disney+ plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (EntityURLHandler,)
    TMDB_PROVIDER_NAMES = ("Disney+",)
    FAVICON_URL = "https://www.disneyplus.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "disneyplus.com"

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Disney+"
