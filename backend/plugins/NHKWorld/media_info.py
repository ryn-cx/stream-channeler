# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.NHKWorld.files import FileMixin
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginWatchProviderItem


# TODO: Validate
class MediaInfoMixin(FileMixin, register=False):
    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        program_file = self.video_program_file(media_identifier)
        program_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        program = program_file.parsed()
        return PluginMediaInfo(
            title=program.title,
            media_type="TV Show",
            overview=program.description or None,
            poster_url=self._get_image_url(program.images.portrait),
            backdrop_url=self._get_image_url(program.images.landscape),
            status="Ended" if program.is_closed else "Ongoing",
            number_of_episodes=program.video_episodes.total,
            genres=[category.name for category in program.categories],
            providers=[
                PluginWatchProviderItem(
                    name=self.plugin_name(),
                    icon_url=self.favicon_url(),
                    plugin_key=self.plugin_key(),
                    search_url=self.build_url(program.url),
                ),
            ],
        )
