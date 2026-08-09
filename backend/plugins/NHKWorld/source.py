# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from loguru import logger

from app.shows.models import Show
from app.sources.models import Source
from plugins.NHKWorld.files import FileMixin, NewVideoEpisodes


class SourceMixin(FileMixin, register=False):
    @override
    def update_source(self, source: Source) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_feed_file = self.new_video_episodes_file(source.data_timestamp)
        new_feed_file.download_if_outdated(source.update_at)
        self._process_new_episodes_files(source)
        self._upsert_source()

    def _process_new_episodes_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_shows=True).all()

        new_files = self.get_incomplete_files(
            NewVideoEpisodes,
            self.new_video_episodes_file,
        )
        for feed_file in new_files:
            logger.info(
                "Processing new episodes file: {}",
                feed_file.database_record.key,
            )
            for item in feed_file.items():
                show_id = item.video_program.id
                if show := Show.get_from_memory(self.session, source, show_id):
                    logger.info("Matched show: {}", show.name or show_id)
                    show.set_update_at(item.video.published_at)
                else:
                    # NHK World has a small library so new shows can be imported
                    # immediately.
                    logger.info("Importing new show: {}", show_id)
                    self._download_show_files_and_children(show_id)
                    self.upsert_show(source, show_id)

            feed_file.database_record.extra = "Completed"

    def _upsert_source(self) -> Source:
        if not (latest_feed_file := self.latest_new_video_episodes_file()):
            latest_feed_file = self._initial_file(NewVideoEpisodes)
            latest_feed_file.download_if_outdated()
        data_timestamp = latest_feed_file.data_timestamp
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
            update_at=data_timestamp + timedelta(days=1),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())
