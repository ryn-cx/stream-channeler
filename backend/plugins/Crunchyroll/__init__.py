# TODO: Validate
"""Crunchyroll plugin.

Detects new media much faster than JustWatch and supports music.
"""

from __future__ import annotations

from typing import override

from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.Crunchyroll.music_keys import MUSIC_SOURCE, VIDEO_SOURCE
from plugins.Crunchyroll.search import SearchMixin
from plugins.Crunchyroll.update import UpdateMixin
from plugins.Crunchyroll.upsert import UpsertMixin
from plugins.Crunchyroll.url_handlers import (
    CrunchyrollArtistURLHandler,
    CrunchyrollConcertURLHandler,
    CrunchyrollEpisodeURLHandler,
    CrunchyrollMusicVideoURLHandler,
    CrunchyrollSeriesURLHandler,
    _CrunchyrollURLHandler,
)
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class Crunchyroll(
    WatchHistoryMixin,
    UpdateMixin,
    UpsertMixin,
    SearchMixin,
    HelperMixin,
    URLHandlerPlugin[_CrunchyrollURLHandler],
    register=True,
):
    """Crunchyroll plugin."""

    _VERSION = "0.0.1"
    TMDB_PROVIDER_NAMES = ("Crunchyroll",)
    FAVICON_URL = (
        "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"
    )

    _URL_HANDLERS = (
        CrunchyrollMusicVideoURLHandler,  # Must be listed first due to URL overlap.
        CrunchyrollConcertURLHandler,
        CrunchyrollArtistURLHandler,
        CrunchyrollSeriesURLHandler,
        CrunchyrollEpisodeURLHandler,
    )

    SHOW_INDEPENDENT_ATTRIBUTES = URLHandlerPlugin.SHOW_INDEPENDENT_ATTRIBUTES | {
        "video_source",
        "music_source",
    }

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    # TODO: Validate
    @override  # Initializes 2 sources instead of 1.
    def initialize_sources(self) -> None:
        if not hasattr(self, "video_source"):
            self.video_source = (
                Source.get(self.session, self.plugin, VIDEO_SOURCE)
                or self._upsert_anime_source()
            )

        if not hasattr(self, "music_source"):
            self.music_source = (
                Source.get(self.session, self.plugin, MUSIC_SOURCE)
                or self._upsert_music_source()
            )

    # TODO: Validate
    @override  # Determines which source to use based on the show key.
    def _import_show(self, show_key: str) -> Show:
        if show := self._preload_show(show_key).one_or_none():
            return show

        _cache = self._download_show_files_and_children(show_key)
        return self.upsert_show(self._source_from_show_key(show_key), show_key)
