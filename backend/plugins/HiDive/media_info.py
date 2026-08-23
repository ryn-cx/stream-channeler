# TODO: Validate
"""Everything HiDive knows about one of its own search results."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from diving_board.series import models as series_models

from app.utils import tz_datetime
from plugins.HiDive.files import vod_hero
from plugins.HiDive.helpers import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE, HelperMixin
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem

_DETAIL_MAX_AGE = timedelta(days=7)

# What a search result's identifier writes in front of the key of a film.
_MOVIE_IDENTIFIER_PREFIX = "VOD"


# TODO: Validate
class MediaInfoMixin(HelperMixin, register=False):
    """Reading a title back for the result it was found as."""

    # TODO: Validate
    @override
    def _media_identifier(self, show_key: str) -> str:
        prefix = _MOVIE_IDENTIFIER_PREFIX if self._is_movie() else "SERIES"
        return f"{prefix}#{show_key}"

    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        type_prefix, _, key = media_identifier.partition("#")
        if type_prefix == _MOVIE_IDENTIFIER_PREFIX:
            return self._movie_media_info(key)
        return self._series_media_info(key)

    # TODO: Validate
    def _series_media_info(self, show_key: str) -> PluginMediaInfo:
        series_file = self.series_file(show_key)
        series_file.download_if_outdated(tz_datetime.now() - _DETAIL_MAX_AGE)
        series_data = series_file.parsed()
        seasons = self._series_season_items(series_data)
        return PluginMediaInfo(
            title=series_data.metadata.series.title,
            media_type=SERIES_MEDIA_TYPE,
            overview=_series_description(series_data),
            poster_url=self._series_image_url(series_data),
            number_of_seasons=len(seasons),
            number_of_episodes=sum(season.episode_count for season in seasons),
            providers=[self._own_provider(self._show_url(show_key))],
        )

    # TODO: Validate
    def _movie_media_info(self, show_key: str) -> PluginMediaInfo:
        vod_file = self.vod_file(show_key)
        vod_file.download_if_outdated(tz_datetime.now() - _DETAIL_MAX_AGE)
        hero = vod_hero(vod_file.parsed())
        release_date = self._release_date(hero)
        return PluginMediaInfo(
            title=self._movie_title(hero),
            media_type=MOVIE_MEDIA_TYPE,
            overview=self._movie_description(hero),
            poster_url=self._hero_image_url(hero),
            year=release_date.year if release_date else None,
            runtime=self._movie_duration(hero),
            providers=[
                self._own_provider(self._show_url(show_key, MOVIE_MEDIA_TYPE)),
            ],
        )

    # A HiDive result is on HiDive, so the one place to watch it is the title's
    # own page rather than anything that has to be searched for.
    # TODO: Validate
    @classmethod
    def _own_provider(cls, url: str) -> PluginWatchProviderItem:
        return PluginWatchProviderItem(
            name=cls.plugin_name(),
            icon_url=cls.FAVICON_URL,
            plugin_key=cls.plugin_key(),
            search_url=url,
        )


# TODO: Validate
def _series_description(series_data: series_models.SeriesModel) -> str | None:
    """Return what the series is about, from the first block of text about it."""
    for element in series_data.elements:
        for content in element.attributes.content or []:
            if content.attributes.text:
                return content.attributes.text
    return None
