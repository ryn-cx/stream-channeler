# TODO: Validate
"""HBO Max plugin."""

from __future__ import annotations

from typing import override

from plugins.HBOMax.handlers import HBOMaxURLHandler, MovieURLHandler, ShowURLHandler
from plugins.HBOMax.helpers import HelperMixin
from plugins.HBOMax.source import SourceMixin
from plugins.HBOMax.upsert import UpsertMixin
from plugins.utils.base_plugin.media_type import MediaTypeImportMixin


class HBOMax(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    MediaTypeImportMixin[HBOMaxURLHandler],
    register=True,
):
    """HBO Max plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (MovieURLHandler, ShowURLHandler)
    TMDB_PROVIDER_NAMES = ("HBO Max", "Max")
    FAVICON_URL = "https://www.hbomax.com/favicon.ico"

    @classmethod
    @override
    def domains(cls) -> list[str]:
        return ["play.hbomax.com", "hbomax.com"]

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://play.hbomax.com/show/ab553cdc-e15d-4597-b65f-bec9201fd2dd`\n\n"
            "> [!TIP/Movie]\n"
            "> `https://play.hbomax.com/movie/4ee4f57e-19bd-493f-96f9-ad3e753af981`\n\n"
        )

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HBO Max"
