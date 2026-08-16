# TODO: Validate
"""Everything Prime Video knows about one of its own search results."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Amazon.files import MOVIE_ENTITY_TYPE
from plugins.Amazon.helpers import HelperMixin
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem

_DETAIL_MAX_AGE = timedelta(days=7)


# TODO: Validate
class MediaInfoMixin(HelperMixin, register=False):
    """Reading a title back for the result it was found as."""

    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        detail_file = self.detail_file(media_identifier)
        detail_file.download_if_outdated(tz_datetime.now() - _DETAIL_MAX_AGE)
        is_movie = detail_file.entity_type() == MOVIE_ENTITY_TYPE
        seasons = detail_file.seasons()
        return PluginMediaInfo(
            title=detail_file.series_title(),
            media_type=detail_file.entity_type(),
            overview=detail_file.synopsis(),
            poster_url=detail_file.image_url(),
            year=detail_file.release_year(),
            number_of_seasons=None if is_movie else len(seasons),
            runtime=detail_file.duration(),
            genres=detail_file.genres(),
            providers=[
                PluginWatchProviderItem(
                    name=self.plugin_name(),
                    icon_url=self.FAVICON_URL,
                    plugin_key=self.plugin_key(),
                    search_url=self._detail_url(detail_file.compact_key()),
                ),
                *[
                    PluginWatchProviderItem(name=channel.name)
                    for channel in detail_file.channels()
                ],
            ],
        )
