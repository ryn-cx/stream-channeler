# TODO: Validate
"""Everything Tubi knows about one of its own titles."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Tubi.helpers import HelperMixin
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem

_CONTENT_MAX_AGE = timedelta(days=7)


# TODO: Validate
class MediaInfoMixin(HelperMixin, register=False):
    """Reading a title back for the result it was found as."""

    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        content_file = self.content_file(media_identifier)
        content_file.download_if_outdated(tz_datetime.now() - _CONTENT_MAX_AGE)
        content = content_file.parsed()
        is_movie = self._is_movie(media_identifier)
        return PluginMediaInfo(
            title=content.title,
            media_type="Movie" if is_movie else "Series",
            overview=content.description,
            poster_url=self._first_image(content.posterarts),
            backdrop_url=self._first_image(content.backgrounds),
            year=content.year,
            number_of_seasons=None
            if is_movie
            else len(self._seasons(media_identifier)),
            runtime=content.duration,
            genres=content.tags,
            providers=[
                PluginWatchProviderItem(
                    name=self.plugin_name(),
                    icon_url=self.FAVICON_URL,
                    plugin_key=self.plugin_key(),
                    search_url=self._movie_url(media_identifier)
                    if is_movie
                    else self._series_url(media_identifier),
                ),
            ],
        )
