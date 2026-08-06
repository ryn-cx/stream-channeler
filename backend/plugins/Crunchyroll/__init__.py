# TODO: Validate
"""Crunchyroll plugin.

Detects new media much faster than JustWatch and supports music.
"""

from __future__ import annotations

from typing import override

from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.Crunchyroll.music_keys import MUSIC_SOURCE_KEY, is_artist_show_key
from plugins.Crunchyroll.update import UpdateMixin
from plugins.Crunchyroll.upsert import UpsertMixin
from plugins.Crunchyroll.url_handlers import (
    CrunchyrollArtistURLHandler,
    CrunchyrollConcertURLHandler,
    CrunchyrollEpisodeURLHandler,
    CrunchyrollMusicVideoURLHandler,
    CrunchyrollSeriesURLHandler,
    CrunchyrollURLHandler,
)
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class Crunchyroll(
    WatchHistoryMixin,
    # TODO: Searching is temporarily disabled, add SearchMixin back to re-enable.
    UpdateMixin,
    UpsertMixin,
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

    # The music handlers come first because `/watch/musicvideo/...` would
    # otherwise have to be told apart from `/watch/...` by the episode handler.
    _URL_HANDLERS = (
        CrunchyrollMusicVideoURLHandler,
        CrunchyrollConcertURLHandler,
        CrunchyrollArtistURLHandler,
        CrunchyrollSeriesURLHandler,
        CrunchyrollEpisodeURLHandler,
    )

    # Both `Source` records describe the plugin rather than a show, so a change
    # of show has to leave them alone.
    SHOW_INDEPENDENT_ATTRIBUTES = URLHandlerPlugin.SHOW_INDEPENDENT_ATTRIBUTES | {
        "video_source",
        "music_source",
    }

    video_source: Source
    """The `Source` every series is stored under."""

    music_source: Source
    """The `Source` every artist is stored under."""

    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    @override
    def initialize_sources(self) -> None:
        """Bind both `Source` records, creating either one that is missing.

        `BasePlugin.source` is deliberately left unset: neither catalogue is the
        default one, so everything here names the source it means.
        """
        if hasattr(self, "video_source"):
            return

        self.video_source = (
            Source.get(
                self.session,
                self.plugin,
                self.plugin_key(),
            )
            or self._upsert_video_source()
        )

        self.music_source = (
            Source.get(
                self.session,
                self.plugin,
                MUSIC_SOURCE_KEY,
            )
            or self._upsert_music_source()
        )

    @override
    def _import_show(self, show_key: str) -> Show:
        """Import a show into whichever of the plugin's two sources it belongs to.

        Reimplemented rather than deferring to `BasePlugin`, which would upsert
        against the single `source` this plugin does not have.
        """
        if show := self._preload_show(show_key).one_or_none():
            return show

        source = (
            self.music_source if is_artist_show_key(show_key) else self.video_source
        )
        _cache = self._download_show_files_and_children(show_key)
        return self.upsert_show(source, show_key)
