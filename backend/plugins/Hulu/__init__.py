# TODO: Validate
"""Hulu plugin."""

from __future__ import annotations

from typing import override

from plugins.Hulu.handlers import HuluURLHandler, MovieURLHandler, SeriesURLHandler
from plugins.Hulu.helpers import HelperMixin
from plugins.Hulu.search import SearchMixin
from plugins.Hulu.source import SourceMixin
from plugins.Hulu.upsert import UpsertMixin
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


class Hulu(
    SourceMixin,
    UpsertMixin,
    SearchMixin,
    HelperMixin,
    MediaTypeImportMixin[HuluURLHandler],
    register=True,
):
    """Hulu plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (SeriesURLHandler, MovieURLHandler)
    TMDB_PROVIDER_NAMES = ("Hulu",)
    FAVICON_URL = "https://www.hulu.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.hulu.com/series/fdeb1018-4472-442f-ba94-fb087cdea069`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://www.hulu.com/movie/4ee4f57e-19bd-493f-96f9-ad3e753af981`\n\n"
        )
