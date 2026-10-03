# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.titles.models import Title
from plugins.Crunchyroll.anime_importer import CrunchyrollAnimeShared
from plugins.Crunchyroll.constants import MUSIC_SOURCE, VIDEO_SOURCE
from plugins.Crunchyroll.files import (
    BaseBrowseSeries,
    BrowseMusic,
    BrowseSeries,
    Catalogue,
)
from plugins.Crunchyroll.music_importer import CrunchyrollMusicShared
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.watch_history import CrunchyrollWatchHistoryMixin
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from datetime import datetime

    from chirashi.browse_music.models import Datum as BrowseMusicDatum
    from chirashi.browse_series.models import Datum as BrowseSeriesDatum

    from app.files.models import File
    from app.sources.models import Source


# TODO: Validate
class CrunchyrollAnimeUpdater(CrunchyrollAnimeShared, BasePluginUpdater):
    # TODO: Validate
    def catalogue_file(self) -> Catalogue:
        return self._cached_file(Catalogue, "alphabetical")

    # TODO: Validate
    def browse_file(self, record: File | None = None) -> BrowseSeries:
        """Return data for recently aired titles."""
        if record is None:
            return self._cached_file(BrowseSeries)
        return self._cached_file(
            BrowseSeries,
            BrowseSeries.file_to_unique_identifier(record),
        )

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BaseBrowseSeries]:
        return [self.browse_file(), self.catalogue_file()]

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        catalogue_file = self.catalogue_file()
        catalogue_file.download_if_outdated()
        return [self.title_url(release.id) for release in catalogue_file.datums()]

    # TODO: Validate
    @override
    def create_initial_channel_records(self) -> None:
        super().create_initial_channel_records()
        self.catalogue_file().clear_status()

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:
        data = self.similar_to_file(title.key).parsed().data
        return [self.title_url(datum.id) for datum in data]

    # TODO: Validate
    def catalogue_from_record(self, record: File) -> Catalogue:
        return self._cached_file(
            Catalogue,
            Catalogue.file_to_unique_identifier(record),
        )

    # TODO: Validate
    def _create_channel_records_from_incomplete_browse_files(self) -> None:
        incomplete_files: list[BaseBrowseSeries] = [
            *self._incomplete_files(BrowseSeries, self.browse_file),
            *self._incomplete_files(Catalogue, self.catalogue_from_record),
        ]
        for browse_json in incomplete_files:
            self._add_titles_to_all_titles_channel(
                release.id for release in browse_json.datums()
            )
            browse_json.clear_status()

    # TODO: Validate
    def _mark_new_titles_as_outdated(self, releases: list[BrowseSeriesDatum]) -> None:
        _cache = self._preload_sources(self.source_name(), preload_seasons=True).all()
        for release in releases:
            if title := Title.get_from_memory(
                self.session,
                self._sources[self.source_name()],
                release.id,
            ):
                # last_public appears to represent the last time a public change
                # was made to the title's data. There is no way to detect what
                # season the update is for so both title and season need to be set
                # to be updated because the season will detect new episodes for
                # existing seasons and the titles will detect new seasons.
                title.set_update_at(release.last_public)
                for season in title.seasons:
                    season.set_update_at(release.last_public)

    # TODO: Validate
    @override
    def _process_source_files(self) -> None:
        self._create_channel_records_from_incomplete_browse_files()
        self._mark_new_titles_as_outdated(
            [
                release
                for browse_file in self._source_files()
                for release in browse_file.datums()
            ],
        )
        catalogue_file = self.catalogue_file()
        self._mark_titles_with_changed_listings(
            self.source_name(),
            {
                release.id: [
                    release.series_metadata.season_count,
                    release.series_metadata.episode_count,
                ]
                for release in catalogue_file.datums()
            },
            catalogue_file.record_data_timestamp,
        )


# TODO: Validate
class CrunchyrollMusicUpdater(CrunchyrollMusicShared, BasePluginUpdater):
    # TODO: Validate
    @classmethod
    @override
    def _link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    def browse_file(self) -> BrowseMusic:
        """BrowseMusic contains data for all of the music."""
        return self._cached_file(BrowseMusic, "artists")

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BrowseMusic]:
        return [self.browse_file()]

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        browse_file = self.browse_file()
        browse_file.download_if_outdated()
        return [self.title_url(artist.id) for artist in browse_file.datums()]

    # TODO: Validate
    @override
    def create_initial_channel_records(self) -> None:
        self.add_new_urls_to_channel("All Music", self._title_urls_from_files())

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:  # noqa: ARG002
        return []

    def _add_artists_to_all_music_channel(self, browse_file: BrowseMusic) -> None:
        urls = [self.title_url(artist.id) for artist in browse_file.datums()]
        self.add_new_urls_to_channel("All Music", urls)

    # TODO: Validate
    def _mark_artists_as_outdated(self, artists: list[BrowseMusicDatum]) -> None:
        _cache = self._preload_sources(self.source_name(), preload_seasons=True).all()
        for artist in artists:
            if title := Title.get_from_memory(
                self.session,
                self._sources[self.source_name()],
                artist.id,
            ):
                title.set_update_at(artist.updated_at)
                # For simplicity set the Title and the Seasons to both be outdated.
                for season in title.seasons:
                    season.set_update_at(artist.updated_at)

    # TODO: Validate
    @override
    def _process_source_files(self) -> None:
        browse_file = self.browse_file()
        artists = browse_file.datums()
        self._add_artists_to_all_music_channel(browse_file)
        self._mark_artists_as_outdated(artists)
        new_title_keys = {artist.id for artist in artists}
        self._mark_mismatched_titles_as_outdated(
            self.source_name(),
            new_title_keys,
            self._source_files_data_timestamp(),
        )


# TODO: Validate
class CrunchyrollUpdater(
    CrunchyrollWatchHistoryMixin,
    CrunchyrollShared,
    BasePluginUpdater,
):
    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (VIDEO_SOURCE, MUSIC_SOURCE)

    # TODO: Validate
    def _source_updaters(
        self,
    ) -> tuple[CrunchyrollAnimeUpdater, CrunchyrollMusicUpdater]:
        return (
            CrunchyrollAnimeUpdater(self.session, self.plugin, self._file_cache),
            CrunchyrollMusicUpdater(self.session, self.plugin, self._file_cache),
        )

    # TODO: Validate
    def _source_updater(
        self,
        source_key: str,
    ) -> CrunchyrollAnimeUpdater | CrunchyrollMusicUpdater:
        if source_key == MUSIC_SOURCE:
            return CrunchyrollMusicUpdater(self.session, self.plugin, self._file_cache)
        return CrunchyrollAnimeUpdater(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def create_initial_source_records(self) -> None:
        anime_source, music_source = self._source_updaters()
        anime_source.upsert_source(VIDEO_SOURCE)
        music_source.upsert_source(MUSIC_SOURCE)

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return [
            url
            for source_updater in self._source_updaters()
            for url in source_updater._title_urls_from_files()  # noqa: SLF001
        ]

    # TODO: Validate
    @override
    def create_initial_channel_records(self) -> None:
        for source_updater in self._source_updaters():
            source_updater.create_initial_channel_records()

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._source_updater(title.source.key).similar_title_urls(title)

    # TODO: Validate
    @override
    def update_file(self, file: File) -> None:
        for source_updater in self._source_updaters():
            if source_updater.handles_file(file):
                source_updater.update_file(file)
                return
        super().update_file(file)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        self._source_updater(source.key).update_source(source, update_at)
