# TODO: Validate

from __future__ import annotations

from typing import override

from plugins.Crunchyroll.helpers import HelperMixin
from plugins.Crunchyroll.search import SearchMixin
from plugins.Crunchyroll.update import UpdateMixin
from plugins.Crunchyroll.upsert import UpsertMixin
from plugins.Crunchyroll.url_handlers import (
    CrunchyrollEpisodeURLHandler,
    CrunchyrollSeriesURLHandler,
    CrunchyrollURLHandler,
)
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Crunchyroll(
    WatchHistoryMixin,
    SearchMixin,
    UpsertMixin,
    UpdateMixin,
    HelperMixin,
    URLHandlerPlugin[CrunchyrollURLHandler],
    register=True,
):
    """Crunchyroll plugin."""

    _VERSION = "0.0.1"
    TMDB_PROVIDER_NAMES = ("Crunchyroll",)
    FAVICON_URL = (
        "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"
    )

    _URL_HANDLERS = (CrunchyrollSeriesURLHandler, CrunchyrollEpisodeURLHandler)

    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"
