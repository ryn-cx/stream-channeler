# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from loguru import logger

from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Crunchyroll.files import BrowseSeries
from plugins.Crunchyroll.helpers import HelperMixin


class SourceMixin(HelperMixin, register=False):
    @override
    def update_source(self, source: Source) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_browse_file = self.browse_series_file(source.data_timestamp)
        new_browse_file.download_if_outdated()
        self._process_new_browse_files(source)
        self._upsert_source()

    def _process_new_browse_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_seasons=True).all()

        for browse_json in self.get_incomplete_files(
            BrowseSeries,
            self.browse_series_file_from_record,
        ):
            logger.info("Processing browse file: {}", browse_json.database_record.key)
            for release in browse_json.extract_datums():
                if show := Show.get_from_memory(self.session, source, release.id):
                    logger.info("Matched show: {}", show.name or release.id)
                    # last_public appears to represent the last time a public change
                    # was made to the show's data. There is no way to detect what
                    # season the update is for so both show and season need to be set
                    # to be updated because the season will detect new episodes for
                    # existing seasons and the shows will detect new seasons.
                    show.set_update_at(release.last_public)
                    for season in show.seasons:
                        season.set_update_at(release.last_public)

            browse_json.database_record.extra = "Completed"

    def _upsert_source(self) -> Source:
        if not (latest_browse_file := self.get_newest_browse_file()):
            latest_browse_file = self.browse_series_file(tz_datetime.now())
            latest_browse_file.download_if_outdated()
        data_timestamp = latest_browse_file.data_timestamp

        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
            data_timestamp=data_timestamp,
            update_at=data_timestamp + timedelta(days=1),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())
