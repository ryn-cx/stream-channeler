# TODO: Validate
"""Crunchyroll plugin.

Detects new media much faster than JustWatch and supports music.
"""

from __future__ import annotations

from typing import override

from app.shows.models import Show
from plugins.Crunchyroll.constants import MUSIC_SOURCE, VIDEO_SOURCE, show_is_an_artist
from plugins.Crunchyroll.search import SearchMixin
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
from plugins.Crunchyroll.utils import HelperMixin
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.TMDB import TMDB
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class Crunchyroll(
    WatchHistoryMixin,
    UpdateMixin,
    UpsertMixin,
    SearchMixin,
    HelperMixin,
    URLHandlerPlugin[CrunchyrollURLHandler],
    register=True,
):
    """Crunchyroll plugin."""

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("Crunchyroll",)

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"

    # TODO: Validate
    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[CrunchyrollURLHandler], ...]:
        return (
            CrunchyrollMusicVideoURLHandler,  # Must be listed first due to URL overlap.
            CrunchyrollConcertURLHandler,
            CrunchyrollArtistURLHandler,
            CrunchyrollSeriesURLHandler,
            CrunchyrollEpisodeURLHandler,
        )

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    # TODO: Validate
    @override  # Initializes 2 sources instead of 1.
    def initialize_sources(self) -> None:
        self._initialize_source(VIDEO_SOURCE, self._anime_source)
        self._initialize_source(MUSIC_SOURCE, self._music_source)

    # TODO: Validate
    @override  # Determines which source to use based on the show key.
    def _import_handler(
        self,
        handler: CrunchyrollURLHandler,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = handler.show_key
        source = handler.source
        if not force and (show := self._preload_show(show_key).one_or_none()):
            return handler.import_results(show)

        # The files come down first because the search is made on the name and
        # year Crunchyroll's own file gives, and a caller that already named the
        # title is not searched for at all.
        _cache = self._download_show_files_and_children(show_key)
        if canonical_show is None:
            canonical_show = self._tmdb_show(show_key, force=force)
            if not force and (show := self._preload_show(show_key).one_or_none()):
                return handler.import_results(show)

        show = self.upsert_show(source, show_key, canonical_show, force=force)
        return handler.import_results(show)

    # TODO: Validate
    @override  # Crunchyroll's own music has no TMDB title to be searched for.
    def _tmdb_show(self, show_key: str, *, force: bool = False) -> Show | None:
        # Music is Crunchyroll's own, so there is no TMDB title to be of.
        if show_is_an_artist(show_key):
            return None

        series_data = self._series_datum(show_key)
        return TMDB(self.session).import_search(
            series_data.title,
            self.tmdb_media_type(show_key),
            series_data.series_launch_year,
            force=force,
        )
