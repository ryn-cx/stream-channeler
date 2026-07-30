# TODO: Validate
"""Pluto TV plugin."""

from __future__ import annotations

from typing import ClassVar, override

from plugins.Pluto.handlers import MovieURLHandler, PlutoURLHandler, SeriesURLHandler
from plugins.Pluto.helpers import HelperMixin
from plugins.Pluto.source import SourceMixin
from plugins.Pluto.upsert import UpsertMixin
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


class Pluto(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    MediaTypeImportMixin[PlutoURLHandler],
    register=True,
):
    """Pluto TV plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[PlutoURLHandler], ...]] = (
        MovieURLHandler,
        SeriesURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("Pluto TV",)
    FAVICON_URL = "https://pluto.tv/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "pluto.tv"

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://pluto.tv/en/on-demand/series/5ef05c6acdce3c001a779a79/details`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://pluto.tv/en/on-demand/movies/68a54f49df1220b53566f16e/details`\n\n"
        )

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Pluto TV"
