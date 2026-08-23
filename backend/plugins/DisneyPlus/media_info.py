# TODO: Validate
"""Everything Disney+ knows about one of its own titles."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.DisneyPlus.helpers import HelperMixin
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem

_ENTITY_MAX_AGE = timedelta(days=7)

_MILLISECONDS_PER_SECOND = 1000


# TODO: Validate
class MediaInfoMixin(HelperMixin, register=False):
    """Reading a title back for the result it was found as."""

    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        entity_file = self.entity_file(media_identifier)
        entity_file.download_if_outdated(tz_datetime.now() - _ENTITY_MAX_AGE)
        is_movie = self._is_movie(media_identifier)
        details = self._media_details(media_identifier)
        hero = self._hero(media_identifier)
        runtime_ms = hero.runtime_ms
        return PluginMediaInfo(
            title=details.title,
            media_type="Movie" if is_movie else "Series",
            overview=details.summary,
            backdrop_url=self._background_image_url(media_identifier),
            year=self._release_year(media_identifier),
            number_of_seasons=None
            if is_movie
            else len(self._seasons(media_identifier)),
            runtime=None
            if runtime_ms is None
            else runtime_ms // _MILLISECONDS_PER_SECOND,
            genres=details.genres or hero.genres or [],
            providers=[
                PluginWatchProviderItem(
                    name=self.plugin_name(),
                    icon_url=self.FAVICON_URL,
                    plugin_key=self.plugin_key(),
                    search_url=self._show_url(media_identifier),
                ),
            ],
        )
