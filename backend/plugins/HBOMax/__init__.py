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

    # TODO: Validate
    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[HBOMaxURLHandler], ...]:
        return (MovieURLHandler, ShowURLHandler)

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("HBO Max", "Max")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hbomax.com/favicon.ico"

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
