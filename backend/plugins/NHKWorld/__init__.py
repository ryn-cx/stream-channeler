# TODO: Validate
from __future__ import annotations

from typing import ClassVar, override

from plugins.NHKWorld.files import FileMixin
from plugins.NHKWorld.handlers import NHKWorldURLHandler, ShowURLHandler
from plugins.NHKWorld.search import SearchMixin
from plugins.NHKWorld.source import SourceMixin
from plugins.NHKWorld.upsert import UpsertMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class NHKWorld(
    SourceMixin,
    UpsertMixin,
    SearchMixin,
    FileMixin,
    URLHandlerPlugin[NHKWorldURLHandler],
    register=True,
):
    _VERSION = "0.0.1"

    # TODO: Add support for single episodes
    _URL_HANDLERS: ClassVar[tuple[type[NHKWorldURLHandler], ...]] = (ShowURLHandler,)
    # TODO: Don't hardcode the favicon URL
    FAVICON_URL = "https://www3.nhk.or.jp/nhkworld/common/site_images/nw_webapp.ico"

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Show]\n"
            "> `https://www3.nhk.or.jp/nhkworld/en/shows/japanologyplus/`\n\n"
        )

    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "NHK World"
