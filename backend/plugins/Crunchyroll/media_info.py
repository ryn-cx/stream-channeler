# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Crunchyroll.helpers import HelperMixin, SizedImage
from plugins.Crunchyroll.music_keys import is_music_show_key
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem

_DETAIL_MAX_AGE = timedelta(days=7)

# Crunchyroll files a series' genres alongside tags that are settings rather
# than genres, and those are the ones written as `name:value`.
_KEYWORD_SEPARATOR = ":"


# TODO: Validate
class MediaInfoMixin(HelperMixin, register=False):
    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        if is_music_show_key(media_identifier):
            return self._artist_media_info(media_identifier)
        return self._series_media_info(media_identifier)

    # TODO: Validate
    def _series_media_info(self, show_key: str) -> PluginMediaInfo:
        series_file = self.series_file(show_key)
        series_file.download_if_outdated(tz_datetime.now() - _DETAIL_MAX_AGE)
        series = series_file.parsed().data[0]
        is_movie = "type:movie" in series.keywords
        return PluginMediaInfo(
            title=series.title,
            media_type="Movie" if is_movie else "Series",
            overview=series.extended_description or series.description or None,
            poster_url=self._largest_source(_flatten(series.images.poster_tall)),
            backdrop_url=self._largest_source(
                _flatten(series.images.poster_wide),
            ),
            year=series.series_launch_year,
            number_of_seasons=None if is_movie else series.season_count,
            number_of_episodes=None if is_movie else series.episode_count,
            genres=[
                keyword
                for keyword in series.keywords
                if _KEYWORD_SEPARATOR not in keyword
            ],
            providers=[self._own_provider(self._series_url(show_key))],
        )

    # TODO: Validate
    def _artist_media_info(self, artist_id: str) -> PluginMediaInfo:
        artist_file = self.artist_file(artist_id)
        artist_file.download_if_outdated(tz_datetime.now() - _DETAIL_MAX_AGE)
        artist = artist_file.parsed().data[0]
        return PluginMediaInfo(
            title=artist.name,
            media_type="Music",
            overview=artist.description or None,
            poster_url=self._largest_source(artist.images.poster_tall),
            backdrop_url=self._largest_source(artist.images.poster_wide),
            number_of_episodes=len(artist.videos) + len(artist.concerts),
            genres=[genre.display_value for genre in artist.genres],
            providers=[self._own_provider(self._artist_url(artist_id))],
        )

    # A Crunchyroll result is on Crunchyroll, so the one place to watch it is
    # the title's own page rather than anything that has to be searched for.
    # TODO: Validate
    @classmethod
    def _own_provider(cls, url: str) -> PluginWatchProviderItem:
        return PluginWatchProviderItem(
            name=cls.plugin_key(),
            icon_url=cls.FAVICON_URL,
            plugin_key=cls.plugin_key(),
            search_url=url,
        )

    # TODO: Validate
    @staticmethod
    def _largest_source(images: Sequence[SizedImage]) -> str | None:
        if not images:
            return None
        return max(images, key=lambda image: image.width).source


# TODO: Validate
def _flatten[ImageT](images: Sequence[Sequence[ImageT]]) -> list[ImageT]:
    return [image for group in images for image in group]
