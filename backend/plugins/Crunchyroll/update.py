# TODO: Validate
from __future__ import annotations

from typing import override

from loguru import logger

from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Crunchyroll.files import BrowseMusic, BrowseSeries
from plugins.Crunchyroll.music_keys import MUSIC_SOURCE_KEY, artist_show_key
from plugins.Crunchyroll.upsert import UpsertMixin


class UpdateMixin(UpsertMixin, register=False):
    @override
    def update_source(self, source: Source) -> None:
        if source.key == MUSIC_SOURCE_KEY:
            self._update_music_source(source)
            return

        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_browse_file = self.browse_series_file(source.data_timestamp)
        new_browse_file.download_if_outdated()
        self._process_new_browse_files(source)
        self._upsert_video_source()

    def _update_music_source(self, source: Source) -> None:
        """Look for new music, which the music `Source` is scheduled for monthly."""
        logger.info("Checking Crunchyroll music for new releases")
        self.browse_music_file(tz_datetime.now()).download_if_outdated()
        self._process_new_music_browse_files(source)
        self._upsert_music_source()

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

    def _process_new_music_browse_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_seasons=True).all()

        for browse_json in self.get_incomplete_files(
            BrowseMusic,
            self.browse_music_file_from_record,
        ):
            logger.info(
                "Processing music browse file: {}",
                browse_json.database_record.key,
            )
            for artist in browse_json.extract_datums():
                show_key = artist_show_key(artist.id)
                if show := Show.get_from_memory(self.session, source, show_key):
                    logger.info("Matched artist: {}", show.name or artist.id)
                    # An artist carries no per-category timestamp, so both of
                    # their seasons are marked alongside the show and whichever
                    # one gained a release picks it up.
                    show.set_update_at(artist.updated_at)
                    for season in show.seasons:
                        season.set_update_at(artist.updated_at)

            browse_json.database_record.extra = "Completed"
