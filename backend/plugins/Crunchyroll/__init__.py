# TODO: Validate
"""Crunchyroll plugin."""

from __future__ import annotations

from typing import override

from plugins.Crunchyroll.handlers import (
    BaseCrunchyrollURLHandler,
    EpisodeURLHandler,
    SeriesURLHandler,
)
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.Crunchyroll.search import SearchMixin
from plugins.Crunchyroll.update import UpdateMixin
from plugins.Crunchyroll.upsert import UpsertMixin
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Crunchyroll(
    WatchHistoryMixin,
    SearchMixin,
    UpsertMixin,
    UpdateMixin,
    HelperMixin,
    URLHandlerPlugin[BaseCrunchyrollURLHandler],
    register=True,
):
    """Crunchyroll plugin."""

    _VERSION = "0.0.1"
    TMDB_PROVIDER_NAMES = ("Crunchyroll",)
    FAVICON_URL = (
        "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"
    )

    _URL_HANDLERS = (SeriesURLHandler, EpisodeURLHandler)

    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.crunchyroll.com/series/GEXH3W29Z/compass20-animation-project`\n\n"
        )
