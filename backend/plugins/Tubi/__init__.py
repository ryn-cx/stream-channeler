# TODO: Validate
"""Tubi plugin."""

from __future__ import annotations

from typing import ClassVar, override

from plugins.Tubi.helpers import HelperMixin
from plugins.Tubi.source import SourceMixin
from plugins.Tubi.upsert import UpsertMixin
from plugins.Tubi.url_handlers import (
    EpisodeURLHandler,
    MovieURLHandler,
    SeriesURLHandler,
    TubiURLHandler,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Tubi(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    URLHandlerPlugin[TubiURLHandler],
    register=True,
):
    """Tubi plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[TubiURLHandler], ...]] = (
        MovieURLHandler,
        SeriesURLHandler,
        EpisodeURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("Tubi TV", "Tubi")
    FAVICON_URL = "https://tubitv.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"
