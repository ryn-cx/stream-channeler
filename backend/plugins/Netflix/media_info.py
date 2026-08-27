# TODO: Validate
"""Everything Netflix knows about one of its own search results."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Netflix.helpers import HelperMixin
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem


# TODO: Validate
class MediaInfoMixin(HelperMixin, register=False):
    """Reading a title back for the result it was found as."""

    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        self.title_file(media_identifier).download_if_outdated(
            tz_datetime.now() - timedelta(days=7),
        )
        video = self._title_video(media_identifier)
        is_movie = self._is_movie(media_identifier)
        seasons = self._ordered_seasons(media_identifier)
        return PluginMediaInfo(
            title=video.title,
            media_type="Movie" if is_movie else "TV Show",
            overview=video.short_synopsis,
            # Netflix pictures a title by the wide art its own page opens with,
            # and offers nothing shaped like a poster alongside it.
            backdrop_url=video.billboard_or_story_art960.url,
            year=video.latest_year,
            number_of_seasons=None if is_movie else len(seasons),
            number_of_episodes=None
            if is_movie
            else sum(len(season.episodes.edges) for season in seasons),
            genres=[edge.node.title for edge in video.genres.edges],
            providers=[
                PluginWatchProviderItem(
                    name=self.plugin_name(),
                    icon_url=self.favicon_url(),
                    plugin_key=self.plugin_key(),
                    search_url=self._show_url(media_identifier),
                ),
            ],
        )
