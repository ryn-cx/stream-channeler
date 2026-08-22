# TODO: Validate
"""Hulu plugin."""

from __future__ import annotations

from typing import override

from plugins.Hulu.media_info import MediaInfoMixin
from plugins.Hulu.search import SearchMixin
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
    SearchMixin,
    MediaInfoMixin,
    SourceMixin,
    MediaTypeImportMixin[HuluURLHandler],
    register=False,
):
    """Hulu plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (SeriesURLHandler, MovieURLHandler, WatchURLHandler)
    TMDB_PROVIDER_NAMES = ("Hulu",)
    FAVICON_URL = "https://www.hulu.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"

