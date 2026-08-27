# TODO: Validate
"""HiDive plugin."""

from __future__ import annotations

from typing import override

from plugins.HiDive.media_info import MediaInfoMixin
from plugins.HiDive.search import SearchMixin
from plugins.HiDive.source import SourceMixin
from plugins.HiDive.upsert import UpsertMixin
from plugins.HiDive.url_handlers import (
    HiDiveURLHandler,
    MovieURLHandler,
    SeasonURLHandler,
    SeriesURLHandler,
)
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin

# TODO: Add support for individual episodes of a series.


# TODO: Validate
class HiDive(
    UpsertMixin,
    SourceMixin,
    SearchMixin,
    MediaInfoMixin,
    MediaTypeImportMixin[HiDiveURLHandler],
    register=True,
):
    """HiDive plugin."""

    # TODO: Validate
    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[HiDiveURLHandler], ...]:
        return (SeriesURLHandler, SeasonURLHandler, MovieURLHandler)

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("HIDIVE",)

    # TODO: Don't hardcode the favicon URL
    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return (
            "https://static.diceplatform.com/prod/original/dce.hidive/settings/"
            "HIDIVE_Logo_iOS_1024x1024_281_29.Y3YMf.vMQ59.png?ts=1727963356"
        )

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hidive.com"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HIDIVE"
