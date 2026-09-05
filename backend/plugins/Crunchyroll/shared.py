# TODO: Validate
"""What the plugin, its importers and its initializer all read Crunchyroll by."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, override

from loguru import logger

from app.canonical_media.service.identifiers import canonical_show_ids_by_key
from app.channels.models import Channel
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Crunchyroll.basic_files import BasicFiles
from plugins.Crunchyroll.files import BrowseMusic, BrowseSeries, chirashi
from plugins.Crunchyroll.utils import (
    MUSIC_SOURCE,
    VIDEO_SOURCE,
    artist_url,
    search_url,
    series_url,
    tenant_category_name,
)
from plugins.utils.base_plugin_v3.files import COMPLETED_STATUS

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID


class CrunchyrollShared(BasicFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Crunchyroll"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (VIDEO_SOURCE, MUSIC_SOURCE)

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str:
        return search_url(query)

    # TODO: Validate
    @property
    def video_source(self) -> Source:
        return self._sources[VIDEO_SOURCE]

    # TODO: Validate
    @property
    def music_source(self) -> Source:
        return self._sources[MUSIC_SOURCE]

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        if source_key == MUSIC_SOURCE:
            return self.upsert_music_source()
        return self.upsert_video_source()

    # TODO: Validate
    def upsert_video_source(self) -> Source:
        return self._upsert_browse_source(
            VIDEO_SOURCE,
            self.newest_browse_series_file(),
            timedelta(days=1),
        )

    # TODO: Validate
    def upsert_music_source(self) -> Source:
        return self._upsert_browse_source(
            MUSIC_SOURCE,
            self.newest_browse_music_file(),
            # Check weekly for new music because updates do not need to be frequent.
            timedelta(days=7),
        )

    # TODO: Validate
    def _upsert_browse_source(
        self,
        source_key: str,
        latest_browse_file: BrowseSeries | BrowseMusic,
        update_interval: timedelta,
    ) -> Source:
        data_timestamp = latest_browse_file.data_timestamp()
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=source_key,
            favicon_url=self.favicon_url(),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(data_timestamp + update_interval)
        return source

    # TODO: Validate
    def add_series_to_plugin_channels(self) -> None:
        catalogue = chirashi().browse_series.extract_data(
            self.catalogue_file().parsed(),
        )
        urls_by_category: dict[str, list[str]] = defaultdict(list)
        keys_by_category: dict[str, list[str]] = defaultdict(list)
        for datum in catalogue:
            for tenant_category in datum.series_metadata.tenant_categories:
                urls_by_category[tenant_category].append(series_url(datum.id))
                keys_by_category[tenant_category].append(datum.id)

        self._replace_plugin_channel_media(
            VIDEO_SOURCE,
            self._channel_description("video_channel_description.md"),
            [series_url(datum.id) for datum in catalogue],
            [datum.id for datum in catalogue],
        )
        for tenant_category in sorted(urls_by_category):
            category_name = tenant_category_name(tenant_category)
            self._replace_plugin_channel_media(
                f"{VIDEO_SOURCE} - {category_name}",
                f"**Every {category_name} series on Crunchyroll.**",
                urls_by_category[tenant_category],
                keys_by_category[tenant_category],
            )

    # TODO: Validate
    def add_music_to_plugin_channels(self) -> None:
        artists = chirashi().browse_music.extract_data(
            self.newest_browse_music_file().parsed(),
        )
        urls_by_genre: dict[str, list[str]] = defaultdict(list)
        keys_by_genre: dict[str, list[str]] = defaultdict(list)
        for artist in artists:
            for genre in artist.genres:
                urls_by_genre[genre.display_value].append(artist_url(artist.id))
                keys_by_genre[genre.display_value].append(artist.id)

        self._replace_plugin_channel_media(
            MUSIC_SOURCE,
            self._channel_description("music_channel_description.md"),
            [artist_url(artist.id) for artist in artists],
            [artist.id for artist in artists],
        )
        for genre_name in sorted(urls_by_genre):
            self._replace_plugin_channel_media(
                f"{MUSIC_SOURCE} - {genre_name}",
                f"**Every {genre_name} artist on Crunchyroll.**",
                urls_by_genre[genre_name],
                keys_by_genre[genre_name],
            )

    # TODO: Validate
    @staticmethod
    def _channel_description(description_file: str) -> str:
        return (Path(__file__).parent / description_file).read_text(encoding="utf-8")

    # TODO: Validate
    def _video_channel(self) -> Channel:
        """Return the plugin owned channel every Crunchyroll series is queued into."""
        return self.add_urls_to_plugin_channel(
            VIDEO_SOURCE,
            self._channel_description("video_channel_description.md"),
        )

    # TODO: Validate
    def _music_channel(self) -> Channel:
        """Return the plugin owned channel every Crunchyroll artist is queued into."""
        return self.add_urls_to_plugin_channel(
            MUSIC_SOURCE,
            self._channel_description("music_channel_description.md"),
        )

    # TODO: Validate
    def _replace_plugin_channel_media(
        self,
        channel_name: str,
        channel_description: str,
        urls: Sequence[str],
        show_keys: Sequence[str],
    ) -> None:
        channel = self.add_urls_to_plugin_channel(
            channel_name,
            channel_description,
            urls,
        )

        canonical_show_ids = self._canonical_show_ids(show_keys)
        for channel_show in list(channel.shows):
            if channel_show.canonical_show_id not in canonical_show_ids:
                self.session.delete(channel_show)
        self.session.commit()

    # TODO: Validate
    def _canonical_show_ids(self, show_keys: Sequence[str]) -> set[UUID]:
        return {
            show_id
            for show_ids in canonical_show_ids_by_key(
                self.session,
                set(show_keys),
            ).values()
            for show_id in show_ids
        }

    # TODO: Validate
    def process_new_browse_files(self) -> None:
        for browse_json in self.get_incomplete_files(
            BrowseSeries,
            self.browse_series_file,
        ):
            # Queueing the series a file found commits, which lets go of every
            # show read for it, and a show nothing holds is not in memory to be
            # matched. Read back per file rather than once, so that a file after
            # the first still recognises the series already imported.
            _cache = self._preload_sources(preload_seasons=True).all()
            logger.info("Processing browse file: {}", browse_json.database_record.key)
            releases = chirashi().browse_series.extract_data(browse_json.parsed())
            new_series_urls: list[str] = []
            for release in releases:
                if show := Show.get_from_memory(
                    self.session,
                    self.video_source,
                    release.id,
                ):
                    logger.info("Matched show: {}", show.name or release.id)
                    # last_public appears to represent the last time a public change
                    # was made to the show's data. There is no way to detect what
                    # season the update is for so both show and season need to be set
                    # to be updated because the season will detect new episodes for
                    # existing seasons and the shows will detect new seasons.
                    show.set_update_at(release.last_public)
                    for season in show.seasons:
                        season.set_update_at(release.last_public)
                else:
                    logger.info("Queueing new series: {}", release.id)
                    new_series_urls.append(series_url(release.id))

            # Queued in one call so the whole browse file costs a single commit.
            if new_series_urls:
                add_urls_to_channel_import_queue(
                    self.session,
                    self._video_channel(),
                    new_series_urls,
                )

            browse_json.database_record.status = COMPLETED_STATUS

    # TODO: Validate
    def process_new_music_browse_files(self) -> None:
        for browse_json in self.get_incomplete_files(
            BrowseMusic,
            self.browse_music_file,
        ):
            # Queueing the artists a file found commits, which lets go of every
            # show read for it, and a show nothing holds is not in memory to be
            # matched. Read back per file rather than once, so that a file after
            # the first still recognises the artists already imported.
            _cache = self._preload_sources(preload_seasons=True).all()
            logger.info(
                "Processing music browse file: {}",
                browse_json.database_record.key,
            )
            artists = chirashi().browse_music.extract_data(browse_json.parsed())
            new_artist_urls: list[str] = []
            for artist in artists:
                if show := Show.get_from_memory(
                    self.session,
                    self.music_source,
                    artist.id,
                ):
                    logger.info("Matched artist: {}", show.name or artist.id)
                    # An artist carries no per-category timestamp, so both of
                    # their seasons are marked alongside the show and whichever
                    # one gained a release picks it up.
                    show.set_update_at(artist.updated_at)
                    for season in show.seasons:
                        season.set_update_at(artist.updated_at)
                else:
                    logger.info("Queueing new artist: {}", artist.id)
                    new_artist_urls.append(artist_url(artist.id))

            # Queued in one call so the whole browse file costs a single commit.
            if new_artist_urls:
                add_urls_to_channel_import_queue(
                    self.session,
                    self._music_channel(),
                    new_artist_urls,
                )

            browse_json.database_record.status = COMPLETED_STATUS

    # TODO: Validate
    def update_video_source(self, source: Source) -> None:
        """Look for new series, which the video `Source` is scheduled for daily."""
        logger.info("Checking Crunchyroll for new releases")
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        self.browse_series_file(source.data_timestamp).download_if_outdated()
        self.process_new_browse_files()
        self.add_series_to_plugin_channels()
        self.upsert_video_source()

    # TODO: Validate
    def update_music_source(self) -> None:
        """Look for new music, which the music `Source` is scheduled for weekly."""
        logger.info("Checking Crunchyroll music for new releases")
        self.browse_music_file(tz_datetime.now()).download_if_outdated()
        self.process_new_music_browse_files()
        self.add_music_to_plugin_channels()
        self.upsert_music_source()
