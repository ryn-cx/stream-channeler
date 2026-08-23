# TODO: Validate
"""Everything Hulu knows about one of its own search results."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Hulu.files import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.Hulu.helpers import HelperMixin
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem

_DETAIL_MAX_AGE = timedelta(days=7)


# TODO: Validate
class MediaInfoMixin(HelperMixin, register=False):
    """Reading a title back for the result it was found as."""

    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        media_type, title_key = self.split_media_identifier(media_identifier)
        if media_type == MOVIE_MEDIA_TYPE:
            return self._movie_media_info(title_key)
        return self._series_media_info(title_key)

    # TODO: Validate
    def _movie_media_info(self, movie_id: str) -> PluginMediaInfo:
        movie_file = self.movie_file(movie_id)
        movie_file.download_if_outdated(tz_datetime.now() - _DETAIL_MAX_AGE)
        data = movie_file.parsed()
        entity = data["details"]["entity"]
        return PluginMediaInfo(
            title=data["name"],
            media_type="Movie",
            overview=entity["description"],
            poster_url=self._image_url(data["artwork"]["program.tile"]["path"]),
            year=tz_datetime.fromisoformat(entity["premiere_date"]).year,
            runtime=entity["duration"],
            genres=entity["genre_names"],
            providers=[self._own_provider(movie_id, MOVIE_MEDIA_TYPE)],
        )

    # TODO: Validate
    def _series_media_info(self, series_id: str) -> PluginMediaInfo:
        series_file = self.series_file(series_id)
        series_file.download_if_outdated(tz_datetime.now() - _DETAIL_MAX_AGE)
        data = series_file.parsed()
        entity = data["details"]["entity"]
        return PluginMediaInfo(
            title=data["name"],
            media_type="Series",
            overview=entity["description"],
            poster_url=self._image_url(data["artwork"]["program.tile"]["path"]),
            year=tz_datetime.fromisoformat(entity["premiere_date"]).year,
            number_of_seasons=len(self._season_numbers(series_id)),
            genres=entity["genre_names"],
            providers=[self._own_provider(series_id, SERIES_MEDIA_TYPE)],
        )

    # A Hulu result is on Hulu, so the one place to watch it is the title's own
    # page rather than anything that has to be searched for.
    # TODO: Validate
    @classmethod
    def _own_provider(cls, show_key: str, media_type: str) -> PluginWatchProviderItem:
        return PluginWatchProviderItem(
            name=cls.plugin_name(),
            icon_url=cls.FAVICON_URL,
            plugin_key=cls.plugin_key(),
            search_url=cls._show_url(show_key, media_type),
        )
