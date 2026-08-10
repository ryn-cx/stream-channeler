# TODO: Validate
from __future__ import annotations

from pathlib import Path
from typing import override

from loguru import logger
from sqlmodel import select

from app.channels.models import Channel
from app.channels.service import add_urls_to_channel_import_queue
from app.models import Visibility
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from app.utils import tz_datetime
from plugins.Crunchyroll.files import BrowseMusic, BrowseSeries, chirashi
from plugins.Crunchyroll.music_keys import MUSIC_SOURCE, VIDEO_SOURCE
from plugins.Crunchyroll.upsert import UpsertMixin

MUSIC_CHANNEL_DESCRIPTION_PATH = Path(__file__).parent / "music_channel_description.md"


class UpdateMixin(UpsertMixin, register=False):
    @override
    def update_source(self, source: Source) -> None:
        if source.key == MUSIC_SOURCE:
            self._update_music_source(source)
        elif source.key == VIDEO_SOURCE:
            self._update_video_source(source)

    def _update_video_source(self, source: Source) -> None:
        """Look for new series, which the video `Source` is scheduled for daily."""
        logger.info("Checking Crunchyroll for new releases")
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        self.browse_series_file(source.data_timestamp).download_if_outdated()
        self._process_new_browse_files(source)
        self._upsert_anime_source()

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
            self.browse_series_file,
        ):
            logger.info("Processing browse file: {}", browse_json.database_record.key)
            releases = chirashi().browse_series.extract_data(browse_json.parsed())
            for release in releases:
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
            self.browse_music_file,
        ):
            logger.info(
                "Processing music browse file: {}",
                browse_json.database_record.key,
            )
            artists = chirashi().browse_music.extract_data(browse_json.parsed())
            new_artist_urls: list[str] = []
            for artist in artists:
                show_key = artist.id
                if show := Show.get_from_memory(self.session, source, show_key):
                    logger.info("Matched artist: {}", show.name or artist.id)
                    # An artist carries no per-category timestamp, so both of
                    # their seasons are marked alongside the show and whichever
                    # one gained a release picks it up.
                    show.set_update_at(artist.updated_at)
                    for season in show.seasons:
                        season.set_update_at(artist.updated_at)
                else:
                    logger.info("Queueing new artist: {}", artist.id)
                    new_artist_urls.append(self._artist_url(show_key))

            # Queued in one call so the whole browse file costs a single commit.
            if new_artist_urls:
                add_urls_to_channel_import_queue(
                    self.session,
                    self._music_channel(),
                    new_artist_urls,
                )

            browse_json.database_record.extra = "Completed"

    def _music_channel(self) -> Channel:
        """Returns the plugin owned channel every Crunchyroll artist is queued into.

        Crunchyroll offers no way to browse their music catalogue, so the channel
        collects the whole of it and is created the first time an artist is found
        rather than by hand.
        """
        plugin_user = get_or_create_plugin_user(session=self.session)
        channel = self.session.exec(
            select(Channel)
            .where(Channel.user_id == plugin_user.id)
            .where(Channel.name == MUSIC_SOURCE),
        ).first()
        if channel:
            return channel

        channel = Channel(
            name=MUSIC_SOURCE,
            description=MUSIC_CHANNEL_DESCRIPTION_PATH.read_text(encoding="utf-8"),
            visibility=Visibility.public,
            anonymous=False,
            user_id=plugin_user.id,
        )
        self.session.add(channel)
        self.session.commit()
        return channel
