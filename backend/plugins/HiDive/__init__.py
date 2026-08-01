# TODO: Validate
"""HiDive plugin."""

from __future__ import annotations

from typing import override

from plugins.HiDive.helpers import HelperMixin
from plugins.HiDive.search import SearchMixin

# TODO: Add support for individual episodes of a series.
from plugins.HiDive.source import SourceMixin
from plugins.HiDive.upsert import UpsertMixin
from plugins.HiDive.url_handlers import (
    HiDiveURLHandler,
    MovieURLHandler,
    SeasonURLHandler,
    SeriesURLHandler,
)
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


class HiDive(
    SourceMixin,
    UpsertMixin,
    SearchMixin,
    HelperMixin,
    MediaTypeImportMixin[HiDiveURLHandler],
    register=True,
):
    """HiDive plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (SeriesURLHandler, SeasonURLHandler, MovieURLHandler)
    TMDB_PROVIDER_NAMES = ("HIDIVE",)
    # TODO: Don't hardcode the favicon URL
    FAVICON_URL = (
        "https://static.diceplatform.com/prod/original/dce.hidive/settings/"
        "HIDIVE_Logo_iOS_1024x1024_281_29.Y3YMf.vMQ59.png?ts=1727963356"
    )

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hidive.com"

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HIDIVE"
