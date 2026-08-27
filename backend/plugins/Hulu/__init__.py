# TODO: Validate
"""Hulu plugin."""

from __future__ import annotations

from typing import override

from plugins.Hulu.source import SourceMixin
from plugins.Hulu.upsert import UpsertMixin
from plugins.Hulu.url_handlers import (
    HuluURLHandler,
    MovieURLHandler,
    SeriesURLHandler,
    WatchURLHandler,
)
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


# TODO: Validate
class Hulu(
    UpsertMixin,
    SourceMixin,
    MediaTypeImportMixin[HuluURLHandler],
    register=True,
):
    """Hulu plugin."""

    # TODO: Validate
    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[HuluURLHandler], ...]:
        return (SeriesURLHandler, MovieURLHandler, WatchURLHandler)

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("Hulu",)

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"
