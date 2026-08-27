# TODO: Validate
"""Paramount+ plugin."""

from __future__ import annotations

from typing import override

from plugins.ParamountPlus.source import SourceMixin
from plugins.ParamountPlus.upsert import UpsertMixin
from plugins.ParamountPlus.url_handlers import (
    MovieURLHandler,
    ParamountPlusURLHandler,
    ShowURLHandler,
)
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


# TODO: Validate
class ParamountPlus(
    UpsertMixin,
    SourceMixin,
    MediaTypeImportMixin[ParamountPlusURLHandler],
    register=True,
):
    """Paramount+ plugin."""

    # TODO: Validate
    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[ParamountPlusURLHandler], ...]:
        return (
            MovieURLHandler,
            ShowURLHandler,
        )

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return (
            "Paramount Plus",
            "Paramount+",
            "Paramount+ Amazon Channel",
            "Paramount Plus Essential",
            "Paramount Plus Premium",
        )

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.paramountplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "paramountplus.com"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Paramount+"
