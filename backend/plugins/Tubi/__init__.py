# TODO: Validate
"""Tubi plugin."""

from __future__ import annotations

from typing import override

from plugins.Tubi.media_info import MediaInfoMixin
from plugins.Tubi.source import SourceMixin
from plugins.Tubi.upsert import UpsertMixin
from plugins.Tubi.url_handlers import (
    EpisodeURLHandler,
    MovieURLHandler,
    SeriesURLHandler,
    TubiURLHandler,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class Tubi(
    UpsertMixin,
    MediaInfoMixin,
    SourceMixin,
    URLHandlerPlugin[TubiURLHandler],
    register=False,
):
    """Tubi plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (
        MovieURLHandler,
        SeriesURLHandler,
        EpisodeURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("Tubi TV", "Tubi")
    FAVICON_URL = "https://tubitv.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"
