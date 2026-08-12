# TODO: Validate
"""Pluto TV plugin."""

from __future__ import annotations

from typing import override

from plugins.Pluto.helpers import HelperMixin
from plugins.Pluto.source import SourceMixin
from plugins.Pluto.upsert import UpsertMixin
from plugins.Pluto.url_handlers import (
    MovieURLHandler,
    PlutoURLHandler,
    SeriesURLHandler,
)
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


# TODO: Validate
class Pluto(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    MediaTypeImportMixin[PlutoURLHandler],
    # TODO: Temporarily disabled.
    register=False,
):
    """Pluto TV plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (
        MovieURLHandler,
        SeriesURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("Pluto TV",)
    FAVICON_URL = "https://pluto.tv/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "pluto.tv"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Pluto TV"
