# TODO: Validate
"""Crunchyroll plugin.

Detects new media much faster than JustWatch and supports music.
"""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.shows.models import Show
from app.sources.models import Source
from plugins.Crunchyroll.constants import MUSIC_SOURCE, VIDEO_SOURCE, show_is_an_artist
from plugins.Crunchyroll.import_url import ImportURLMixin
from plugins.Crunchyroll.search import SearchMixin
from plugins.Crunchyroll.update import UpdateMixin
from plugins.Crunchyroll.upsert import UpsertMixin
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.TMDB import TMDB


# TODO: Validate
class Crunchyroll(
    WatchHistoryMixin,
    UpdateMixin,
    UpsertMixin,
    SearchMixin,
    ImportURLMixin,
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
    def _domain(cls) -> str:
        return "crunchyroll.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (VIDEO_SOURCE, MUSIC_SOURCE)

    # TODO: Validate
    @override  # Initializes 2 sources instead of 1.
    def initialize_sources(self) -> None:
        self.initialize_source(VIDEO_SOURCE, self._upsert_anime_source)
        self.initialize_source(MUSIC_SOURCE, self._upsert_music_source)

    # TODO: Validate
    def _upsert_anime_source(self) -> Source:
        return self._upsert_source(
            VIDEO_SOURCE,
            self.find_newest_browse_series_file(),
            self.browse_series_file,
            timedelta(days=1),
        )

    # TODO: Validate
    def _upsert_music_source(self) -> Source:
        return self._upsert_source(
            MUSIC_SOURCE,
            self.find_newest_browse_music_file(),
            self.browse_music_file,
            # Check weekly for new music because updates do not need to be frequent.
            timedelta(days=7),
        )

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
