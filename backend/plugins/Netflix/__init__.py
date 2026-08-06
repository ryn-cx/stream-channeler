# TODO: Validate
from __future__ import annotations

from typing import ClassVar, override

from plugins.Netflix.helpers import HelperMixin
from plugins.Netflix.source import SourceMixin
from plugins.Netflix.upsert import UpsertMixin
from plugins.Netflix.url_handlers import NetflixURLHandler, TitleURLHandler
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Netflix(
    SourceMixin,
    UpsertMixin,
    # TODO: Searching is temporarily disabled, add SearchMixin back to re-enable.
    HelperMixin,
    URLHandlerPlugin[NetflixURLHandler],
    register=True,
):
    _VERSION = "0.0.1"
    TMDB_PROVIDER_NAMES = ("Netflix", "Netflix Standard with Ads")
    FAVICON_URL = "https://www.netflix.com/favicon.ico"

    _URL_HANDLERS: ClassVar[tuple[type[NetflixURLHandler], ...]] = (TitleURLHandler,)

    @classmethod
    @override
    def _domain(cls) -> str:
        return "netflix.com"
