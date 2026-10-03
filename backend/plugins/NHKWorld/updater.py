# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from loguru import logger

from app.titles.models import Title
from plugins.NHKWorld.files import NewVideoEpisodes, VideoPrograms
from plugins.NHKWorld.shared import NHKWorldShared
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Sequence

    from naphki.video_episodes.models import Item

    from app.files.models import File
    from app.sources.models import Source


# TODO: Validate
class NHKWorldUpdater(NHKWorldShared, BasePluginUpdater):
    # TODO: Validate
    @override
    def _import_plugin_files(self) -> None:
        self._create_channel_records_from_incomplete_feed_files()
        self._mark_new_titles_as_outdated(
            self.source,
            self.new_video_episodes_file().items(),
        )

    def _create_channel_records_from_incomplete_feed_files(self) -> None:
        for feed_file in self._incomplete_files(
            NewVideoEpisodes,
            self.new_video_episodes_file,
        ):
            title_keys = [item.video_program.id for item in feed_file.items()]
            self._add_titles_to_all_titles_channel(title_keys)
            feed_file.clear_status()

    # TODO: Validate
    def _mark_new_titles_as_outdated(self, source: Source, items: list[Item]) -> None:
        _cache = self._preload_sources(preload_seasons=True).all()
        for item in items:
            title_id = item.video_program.id
            if title := Title.get_from_memory(self.session, source, title_id):
                logger.info("Matched title: {}", title.name or title_id)
                title.set_update_at(item.video.published_at)
                for season in title.seasons:
                    season.set_update_at(item.video.published_at)

    # TODO: Validate
    def video_programs_file(self) -> VideoPrograms:
        return self._cached_file(VideoPrograms)

    # TODO: Consider making this a generic function
    # TODO: Validate
    def new_video_episodes_file(self, record: File | None = None) -> NewVideoEpisodes:
        """Contains the newest videos on the website."""
        if record is None:
            return self._cached_file(NewVideoEpisodes)
        return self._cached_file(
            NewVideoEpisodes,
            NewVideoEpisodes.file_to_unique_identifier(record),
        )

    # TODO: Validate
    @override
    def _plugin_files(self) -> Sequence[NewVideoEpisodes]:
        return [self.new_video_episodes_file()]

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        self.video_programs_file().download_if_outdated()
        return [self.title_url(item.id) for item in self.video_programs_file().items()]
