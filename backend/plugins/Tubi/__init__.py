# TODO: Validate
"""Tubi plugin."""

from __future__ import annotations

from typing import ClassVar, override

from plugins.Tubi.handlers import (
    EpisodeURLHandler,
    MovieURLHandler,
    SeriesURLHandler,
    TubiURLHandler,
)
from plugins.Tubi.helpers import HelperMixin
from plugins.Tubi.source import SourceMixin
from plugins.Tubi.upsert import UpsertMixin
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

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://tubitv.com/series/300006854/scooby-doo-where-are-you`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://tubitv.com/movies/100029837/megamind`\n\n"
            "> [!TIP/Episode]\n"
            "> `https://tubitv.com/tv-shows/595036`\n\n"
        )
