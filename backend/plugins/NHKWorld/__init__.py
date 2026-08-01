# TODO: Validate
from __future__ import annotations

from typing import ClassVar, override

from plugins.NHKWorld.helpers import HelperMixin
from plugins.NHKWorld.search import SearchMixin
from plugins.NHKWorld.source import SourceMixin
from plugins.NHKWorld.upsert import UpsertMixin
from plugins.NHKWorld.url_handlers import NHKWorldURLHandler, ShowURLHandler
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class NHKWorld(
    SourceMixin,
    UpsertMixin,
    SearchMixin,
    HelperMixin,
    URLHandlerPlugin[NHKWorldURLHandler],
    register=True,
):
    _VERSION = "0.0.1"

    # TODO: Add support for single episodes
    _URL_HANDLERS: ClassVar[tuple[type[NHKWorldURLHandler], ...]] = (ShowURLHandler,)
    # TODO: Don't hardcode the favicon URL
    FAVICON_URL = "https://www3.nhk.or.jp/nhkworld/common/site_images/nw_webapp.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "NHK World"
