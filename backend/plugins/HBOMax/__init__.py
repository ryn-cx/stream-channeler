# TODO: Validate
"""HBO Max plugin."""

from __future__ import annotations

from typing import override

from plugins.HBOMax.source import SourceMixin
from plugins.HBOMax.upsert import UpsertMixin
from plugins.HBOMax.url_handlers import (
    HBOMaxURLHandler,
    MovieURLHandler,
    ShowURLHandler,
)
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


# TODO: Validate
class HBOMax(
    UpsertMixin,
    SourceMixin,
    MediaTypeImportMixin[HBOMaxURLHandler],
    register=True,
):
    """HBO Max plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (MovieURLHandler, ShowURLHandler)
    TMDB_PROVIDER_NAMES = ("HBO Max", "Max")
    FAVICON_URL = "https://www.hbomax.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        return ["play.hbomax.com", "hbomax.com"]

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HBO Max"

