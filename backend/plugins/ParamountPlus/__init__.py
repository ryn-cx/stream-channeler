# TODO: Validate
"""Paramount+ plugin."""

from __future__ import annotations

from typing import ClassVar, override

from plugins.ParamountPlus.helpers import HelperMixin
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
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    MediaTypeImportMixin[ParamountPlusURLHandler],
    # TODO: Temporarily disabled.
    register=False,
):
    """Paramount+ plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[ParamountPlusURLHandler], ...]] = (
        MovieURLHandler,
        ShowURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("Paramount Plus", "Paramount+", "Paramount+ Amazon Channel")
    FAVICON_URL = "https://www.paramountplus.com/favicon.ico"

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
