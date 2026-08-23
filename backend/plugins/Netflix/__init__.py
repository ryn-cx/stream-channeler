# TODO: Validate
"""Netflix plugin."""

from __future__ import annotations

from typing import override

from plugins.Netflix.media_info import MediaInfoMixin
from plugins.Netflix.source import SourceMixin
from plugins.Netflix.upsert import UpsertMixin
from plugins.Netflix.url_handlers import NetflixURLHandler, TitleURLHandler
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class Netflix(
    UpsertMixin,
    # TODO: Searching is temporarily disabled, add SearchMixin back to re-enable.
    MediaInfoMixin,
    SourceMixin,
    URLHandlerPlugin[NetflixURLHandler],
    register=True,
):
    """Netflix plugin."""

    _VERSION = "0.0.1"
    TMDB_PROVIDER_NAMES = ("Netflix", "Netflix Standard with Ads")
    FAVICON_URL = "https://www.netflix.com/favicon.ico"

    _URL_HANDLERS = (TitleURLHandler,)

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"
