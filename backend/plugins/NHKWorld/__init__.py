# TODO: Validate
from __future__ import annotations

from typing import override
from urllib.parse import quote_plus

from plugins.NHKWorld.source import SourceMixin
from plugins.NHKWorld.upsert import UpsertMixin
from plugins.NHKWorld.url_handlers import NHKWorldURLHandler, ShowURLHandler
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class NHKWorld(
    SourceMixin,
    UpsertMixin,
    URLHandlerPlugin[NHKWorldURLHandler],
    register=True,
):
    # TODO: Add support for single episodes
    # TODO: Validate
    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[NHKWorldURLHandler], ...]:
        return (ShowURLHandler,)

    # TODO: Don't hardcode the favicon URL
    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www3.nhk.or.jp/nhkworld/common/site_images/nw_webapp.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "NHK World"

    # TODO: Validate
    @classmethod
    @override
    def manual_search(cls, query: str) -> str:
        return cls.build_url(f"nhkworld/en/shows/search/?q={quote_plus(query)}")
