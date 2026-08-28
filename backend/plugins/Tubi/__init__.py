# TODO: Validate
"""Tubi plugin."""

from __future__ import annotations

from typing import override

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
    SourceMixin,
    URLHandlerPlugin[TubiURLHandler],
    register=True,
):
    """Tubi plugin."""

    # TODO: Validate
    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[TubiURLHandler], ...]:
        return (
            MovieURLHandler,
            SeriesURLHandler,
            EpisodeURLHandler,
        )

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("Tubi TV", "Tubi")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://tubitv.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "tubitv.com"
