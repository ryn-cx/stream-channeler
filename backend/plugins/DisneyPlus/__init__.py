# TODO: Validate
"""Disney+ plugin.

There is no obvious way to get information on episodes after episode 24, so a
long running series is only read as far as that.
"""

from __future__ import annotations

from typing import override

from plugins.DisneyPlus.media_info import MediaInfoMixin
from plugins.DisneyPlus.source import SourceMixin
from plugins.DisneyPlus.upsert import UpsertMixin
from plugins.DisneyPlus.url_handlers import DisneyPlusURLHandler, EntityURLHandler
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class DisneyPlus(
    UpsertMixin,
    MediaInfoMixin,
    SourceMixin,
    URLHandlerPlugin[DisneyPlusURLHandler],
    # Temporarily disabled until a solution is found to get episodes past episode 24
    register=True,
):
    """Disney+ plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (EntityURLHandler,)
    TMDB_PROVIDER_NAMES = ("Disney+",)
    FAVICON_URL = "https://www.disneyplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "disneyplus.com"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Disney+"
