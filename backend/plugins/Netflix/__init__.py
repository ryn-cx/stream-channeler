# TODO: Validate
from __future__ import annotations

from typing import ClassVar, override

from plugins.Netflix.url_handlers import NetflixURLHandler, TitleURLHandler
from plugins.Netflix.helpers import HelperMixin
from plugins.Netflix.search import SearchMixin
from plugins.Netflix.source import SourceMixin
from plugins.Netflix.upsert import UpsertMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Netflix(
    SourceMixin,
    UpsertMixin,
    SearchMixin,
    HelperMixin,
    URLHandlerPlugin[NetflixURLHandler],
    register=True,
):
    _VERSION = "0.0.1"
    TMDB_PROVIDER_NAMES = ("Netflix", "Netflix Standard with Ads")
    FAVICON_URL = "https://www.netflix.com/favicon.ico"

    _URL_HANDLERS: ClassVar[tuple[type[NetflixURLHandler], ...]] = (TitleURLHandler,)

    @classmethod
    def import_url_instructions(cls) -> str:
        return "> [!TIP/Title]\n> `https://www.netflix.com/title/80240027`\n\n"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"
