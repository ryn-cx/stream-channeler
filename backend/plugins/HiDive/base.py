# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.HiDive.files import vod_hero
from plugins.HiDive.source import SourceMixin
from plugins.HiDive.update import UpdateMixin
from plugins.utils.abstract_plugin import TMDBLookupInfo
from plugins.utils.base_plugin_v2.search import BaseCatalogueSearchMixin


# TODO: Validate
class HiDiveBase(UpdateMixin, SourceMixin, BaseCatalogueSearchMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HIDIVE"

    # TODO: Don't hardcode the favicon URL
    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return (
            "https://static.diceplatform.com/prod/original/dce.hidive/settings/"
            "HIDIVE_Logo_iOS_1024x1024_281_29.Y3YMf.vMQ59.png?ts=1727963356"
        )

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hidive.com"

    # TODO: Validate
    @override
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> list[TMDBLookupInfo]:
        if self._is_movie():
            return self._get_movie_tmdb_lookup_info(show_key)
        return self._get_series_tmdb_lookup_info(show_key)

    # TODO: Validate
    def _get_series_tmdb_lookup_info(
        self,
        show_key: str,
    ) -> list[TMDBLookupInfo]:
        series_file = self.series_file(show_key)
        series_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return [
            TMDBLookupInfo(
                series_file.parsed().metadata.series.title,
                TMDBMediaType.tv,
                None,
            ),
        ]

    # TODO: Validate
    def _get_movie_tmdb_lookup_info(
        self,
        show_key: str,
    ) -> list[TMDBLookupInfo]:
        vod_file = self.vod_file(show_key)
        vod_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        hero = vod_hero(vod_file.parsed())
        release_date = self._release_date(hero)
        return [
            TMDBLookupInfo(
                self._movie_title(hero),
                TMDBMediaType.movie,
                release_date.year if release_date else None,
            ),
        ]
