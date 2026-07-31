# TODO: Validate
"""Paramount+ plugin."""

from __future__ import annotations

from typing import ClassVar, override

from plugins.ParamountPlus.url_handlers import (
    MovieURLHandler,
    ParamountPlusURLHandler,
    ShowURLHandler,
)
from plugins.ParamountPlus.helpers import HelperMixin
from plugins.ParamountPlus.source import SourceMixin
from plugins.ParamountPlus.upsert import UpsertMixin
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


class ParamountPlus(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    MediaTypeImportMixin[ParamountPlusURLHandler],
    register=True,
):
    """Paramount+ plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[ParamountPlusURLHandler], ...]] = (
        MovieURLHandler,
        ShowURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("Paramount Plus", "Paramount+", "Paramount+ Amazon Channel")
    FAVICON_URL = "https://www.paramountplus.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "paramountplus.com"

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.paramountplus.com/shows/south-park/`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://www.paramountplus.com/movies/video/ALVE01KT235XQDEK58R7H2012VNZMK/`\n\n"
        )

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Paramount+"
