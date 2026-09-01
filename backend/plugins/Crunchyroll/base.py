# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Crunchyroll.constants import (
    MUSIC_SOURCE,
    VIDEO_SOURCE,
    show_is_an_artist,
)
from plugins.Crunchyroll.search import SearchMixin
from plugins.Crunchyroll.update import UpdateMixin
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.utils.abstract_plugin import TMDBLookupInfo


# TODO: Validate
class CrunchyrollBase(WatchHistoryMixin, UpdateMixin, SearchMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Crunchyroll"

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
    @override
    def get_tmdb_lookup_info(self, show_key: str) -> TMDBLookupInfo | None:
        # Music is Crunchyroll's own, so there is no TMDB title to be of.
        if show_is_an_artist(show_key):
            return None

        series_data = self._series_datum(show_key)
        return TMDBLookupInfo(
            title=series_data.title,
            media_type="Movie" if self._is_movie(show_key) else "Series",
            year=series_data.series_launch_year,
        )
