# TODO: Validate
"""Everything The Roku Channel knows about one of its own titles."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Roku.constants import MOVIE_TYPE
from plugins.Roku.helpers import HelperMixin
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem


# TODO: Validate
class MediaInfoMixin(HelperMixin, register=False):
    """Reading a title back out of the content file it is stored in."""

    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        content_file = self.content_file(media_identifier)
        content_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        content = content_file.parsed()
        is_movie = content.type == MOVIE_TYPE
        episodes = self._show_episodes(media_identifier)
        return PluginMediaInfo(
            title=content.title,
            media_type="Movie" if is_movie else "TV Show",
            overview=content.description,
            poster_url=content.image_map.detail_poster.path,
            backdrop_url=content.image_map.detail_background.path,
            year=content.release_year,
            number_of_seasons=(
                None if is_movie else len(self._season_numbers(media_identifier))
            ),
            number_of_episodes=None if is_movie else len(episodes),
            runtime=content.run_time_seconds,
            genres=content.genres,
            providers=[
                PluginWatchProviderItem(
                    name=self.plugin_name(),
                    icon_url=self.favicon_url(),
                    plugin_key=self.plugin_key(),
                    search_url=self._show_url(media_identifier),
                ),
            ],
        )
