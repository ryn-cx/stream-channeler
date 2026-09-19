# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, override

from loguru import logger

from app.titles.models import Title
from app.utils import tz_datetime
from plugins.NHKWorld.series_importer import NHKWorldSeriesImporter
from plugins.NHKWorld.shared import NHKWorldImporter, NHKWorldShared
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from datetime import datetime

    from naphki.video_episodes.models import Item

    from app.sources.models import Source


# TODO: Validate
class NHKWorld(NHKWorldShared, AbstractPlugin, register=True):
    # TODO: Validate
    @override
    def _next_source_update_at(self) -> datetime:
        return self._source_files_data_timestamp() + timedelta(days=1)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        latest_feed_file = self.latest_new_video_episodes_file()
        feed_datetime = (
            latest_feed_file.record_data_timestamp
            if latest_feed_file
            else tz_datetime.now()
        )
        feed_file = self.new_video_episodes_file(feed_datetime)
        feed_file.download_if_outdated(update_at)
        self._create_channel_records_from_incomplete_feed_files()
        self._mark_new_titles_as_outdated(source, feed_file.items())
        self.upsert_source(source.key)

    # TODO: Validate
    def _mark_new_titles_as_outdated(self, source: Source, items: list[Item]) -> None:
        _cache = self._preload_sources(preload_titles=True).all()
        for item in items:
            title_id = item.video_program.id
            if title := Title.get_from_memory(self.session, source, title_id):
                logger.info("Matched title: {}", title.name or title_id)
                title.set_update_at(item.video.published_at)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> NHKWorldImporter:
        return NHKWorldSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> NHKWorldImporter:
        return NHKWorldSeriesImporter(self.session, self.plugin, self._file_cache)
