# TODO: Validate
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import singledispatchmethod
from typing import TYPE_CHECKING, Any, override

from loguru import logger

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.files.models import File
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.Crunchyroll.constants import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    EPISODE_URL_REGEX,
    MUSIC_CATEGORY_NAMES,
    MUSIC_SOURCE,
    MUSIC_VIDEO_URL_REGEX,
    SERIES_URL_REGEX,
    CrunchyrollMusicCategory,
)
from plugins.Crunchyroll.files import BrowseMusic, BrowseSeries
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.utils import (
    build_url,
    episode_image,
    episode_thumbnail,
    is_movie,
    largest_image,
    nearest_thumbnail,
    title_image,
    title_thumbnail,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import URLTitleInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chirashi.artist_concerts.models import Datum as ConcertListingDatum
    from chirashi.artist_music_videos.models import Datum as MusicVideoListingDatum
    from chirashi.browse_music.models import Datum as BrowseMusicDatum
    from chirashi.browse_series.models import Datum as BrowseSeriesDatum

    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class CrunchyrollImporter(CrunchyrollShared, BaseImporter, ABC):
    # TODO: Validate
    @classmethod
    @abstractmethod
    def _source_update_interval(cls) -> timedelta: ...

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        data_timestamps = self._source_files_data_timestamps()
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=max(data_timestamps),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(
            min(data_timestamps) + self._source_update_interval(),
        )
        return source


# TODO: Validate
class CrunchyrollAnimeImporter(CrunchyrollImporter):
    """Plugin for handling Crunchyroll anime and live-action series.

    Named CrunchyRollAnime because the majority of the titles it handles will be anime
    and this name makes it as clear as possible that it does not import music content.
    """

    # TODO: Validate
    @classmethod
    @override
    def _source_update_interval(cls) -> timedelta:
        # The page lists episodes from newest to oldest, daily checks work best for
        # this.
        return timedelta(days=1)

    # TODO: Validate
    @staticmethod
    def title_url(title_key: str) -> str:
        return build_url(f"series/{title_key}")

    # TODO: Validate
    @staticmethod
    def episode_url(episode_key: str) -> str:
        return build_url(f"watch/{episode_key}")

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.series_file(title_key), url)
            return URLTitleInfo(title_key)

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            episode_key = match.group("episode_key")
            objects_file = self.objects_file(episode_key)
            self.raise_invalid_url_if_no_content(objects_file, url)

            # Episodes for different regions have different keys. The title is always
            # imported using the original region for consistency.
            for version in objects_file.parsed().data[0].episode_metadata.versions:
                if version.original:
                    episode_key = version.guid
                    break

            original_file = self.objects_file(episode_key)
            self.raise_invalid_url_if_no_content(original_file, url)
            return URLTitleInfo(
                original_file.parsed().data[0].episode_metadata.series_id,
                episode_key=episode_key,
            )

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new seasons.
            self.seasons_file(title_key),
            # Required to detect changes to the title.
            self.series_file(title_key),
            self.categories_file(title_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new episodes.
            self.season_episodes_file(season_key),
            # Required to detect changes to the season.
            self.seasons_file(title_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the episode.
        return [self.season_episodes_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            season_data.id for season_data in self.seasons_file(title_key).parsed().data
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            episode.id
            for season_key in season_keys
            for episode in self.season_episodes_file(season_key).parsed().data
        ]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            series_data = self.series_file(title_key).parsed().data[0]
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=series_data.id,
                name=series_data.title,
                description=series_data.description,
                media_type="Movie" if is_movie(series_data) else "Series",
                url=self.title_url(series_data.id),
                image_url=title_image(series_data.images),
                thumbnail_url=title_thumbnail(series_data.images),
                year=series_data.series_launch_year,
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(None)

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        seasons_file = self.seasons_file(title.key)
        for sort_order, season_data in enumerate(seasons_file.parsed().data):
            season = Season.get_from_memory(self.session, title, season_data.id)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self._season_files_data_timestamps(
                    season_data.id, title.key
                )
                season = Season(
                    key=season_data.id,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    sort_order=sort_order,
                    data_timestamp=max(data_timestamps),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_episodes(season, title.key, force=force)
            self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        parsed_season_episodes = self.season_episodes_file(season.key).parsed()
        for sort_order, episode_data in enumerate(parsed_season_episodes.data):
            episode = Episode.get_from_memory(self.session, season, episode_data.id)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            data_timestamps = self._episode_files_data_timestamps(
                episode_data.id,
                season.key,
                title_key,
            )
            episode = Episode(
                key=episode_data.id,
                watch_identifier=watch_identifier(self.plugin_name(), episode_data.id),
                name=episode_data.title,
                episode_number=episode_data.episode_number,
                url=self.episode_url(episode_data.id),
                description=episode_data.description,
                image_url=episode_image(episode_data.images),
                thumbnail_url=episode_thumbnail(episode_data.images),
                duration=episode_data.duration_ms // 1000,
                sort_order=sort_order,
                air_date=episode_data.episode_air_date,
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None)

    # TODO: Validate
    @singledispatchmethod
    def browse_file(
        self,
        browse: datetime | File,  # noqa: ARG002
    ) -> BrowseSeries:
        """Return data for recently aired titles."""
        raise TypeError

    # TODO: Validate
    @browse_file.register
    def _browse_file_by_datetime(self, browse: datetime) -> BrowseSeries:
        return self._cached_file(BrowseSeries, str(browse))

    # TODO: Validate
    @browse_file.register
    def _browse_file_by_record(self, browse: File) -> BrowseSeries:
        return self._cached_file(
            BrowseSeries,
            BrowseSeries.file_to_unique_identifier(browse),
        )

    # TODO: Validate
    def newest_browse_file(self) -> BrowseSeries:
        if file := self.latest_file_record(BrowseSeries):
            return self.browse_file(file)
        newest_browse_file = self.browse_file(tz_datetime.now())
        newest_browse_file.download_if_outdated()
        return newest_browse_file

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BrowseSeries]:
        return [self.newest_browse_file()]

    # TODO: Validate
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # This should not be possible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        for datum in self.categories_file(title.key).parsed().data:
            self._add_urls_to_channel_by_prefix([title.url], datum.localization.title)

    # TODO: Validate
    def create_channel_records(self) -> None:
        catalogue_file = self.catalogue_file()
        catalogue_file.download_if_outdated()
        self._create_channel_records_from_file(catalogue_file.datums())
        for browse_json in self._incomplete_files(BrowseSeries, self.browse_file):
            self._create_channel_records_from_file(browse_json.datums())
            browse_json.clear_status()

    # TODO: Validate
    def _create_channel_records_from_file(
        self,
        releases: list[BrowseSeriesDatum],
    ) -> None:
        self._add_urls_to_channel_by_prefix(
            [self.title_url(release.id) for release in releases],
            "All Titles",
        )

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
    def update_source(self, source: Source, update_at: datetime) -> None:
        browse_file = self.newest_browse_file()
        browse_file.download_if_outdated()
        catalogue_file = self.catalogue_file()
        catalogue_file.download_if_outdated()
        self.create_channel_records()
        self._mark_new_titles_as_outdated(browse_file.datums())
        self._mark_mismatched_titles_as_outdated(
            self.source_name(),
            {release.id for release in catalogue_file.datums()},
            self._source_files_data_timestamps(),
        )
        self.upsert_source(self.source_name())


# TODO: Validate
class CrunchyrollMusicImporter(CrunchyrollImporter):
    # TODO: Validate
    @classmethod
    @override
    def _source_update_interval(cls) -> timedelta:
        # Music isn't that important to be up to date so weekly checks are adequate.
        return timedelta(days=7)

    # TODO: Validate
    @classmethod
    @override
    def source_name(cls) -> str:
        return MUSIC_SOURCE

    # TODO: Validate
    @classmethod
    @override
    def link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    @staticmethod
    def title_url(title_key: str) -> str:
        return build_url(f"artist/{title_key}")

    # TODO: Validate
    @staticmethod
    def episode_url(category: CrunchyrollMusicCategory, episode_key: str) -> str:
        return build_url(f"watch/{category}/{episode_key}")

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MUSIC_VIDEO_URL_REGEX, CONCERT_URL_REGEX, ARTIST_URL_REGEX)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        domain_regex = self._domain_regex()
        for url_regex, group in (
            (MUSIC_VIDEO_URL_REGEX, "music_video_key"),
            (CONCERT_URL_REGEX, "concert_key"),
        ):
            if match := re.match(domain_regex + url_regex, url):
                episode_key = match.group(group)
                music_file = self.concert_or_music_video_file(episode_key)
                self.raise_invalid_url_if_no_content(music_file, url)
                return URLTitleInfo(
                    music_file.parsed().data[0].artist.id,
                    episode_key=episode_key,
                )

        if match := re.match(domain_regex + ARTIST_URL_REGEX, url):
            title_key = match.group("artist_key")
            self.raise_invalid_url_if_no_content(self.artist_file(title_key), url)
            return URLTitleInfo(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect changes to the artist.
            self.artist_file(title_key),
            # Required to detect new music videos and concerts.
            self.artist_music_videos_file(title_key),
            self.artist_concerts_file(title_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new music videos or concerts.
            self.season_file(title_key, CrunchyrollMusicCategory(season_key)),
            # Required to detect changes to the artist.
            self.artist_file(title_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.concert_or_music_video_file(episode_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [category.value for category in CrunchyrollMusicCategory]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            datum.id
            for season_key in season_keys
            for datum in self.season_file(
                title_key,
                CrunchyrollMusicCategory(season_key),
            )
            .parsed()
            .data
        ]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            artist_data = self.artist_file(title_key).parsed().data[0]
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=artist_data.name,
                description=artist_data.description,
                media_type="Music",
                url=self.title_url(title_key),
                image_url=largest_image(artist_data.images.poster_wide),
                thumbnail_url=nearest_thumbnail(artist_data.images.poster_wide),
                data_timestamp=max(data_timestamps),
                canonical_title_validated_at=tz_datetime.now(),
                source_id=source.id,
            ).upsert(source, title)
            # All updates are set by update_source.
            title.set_update_at(None)

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        seasons: list[Season] = []
        for category in CrunchyrollMusicCategory:
            season = Season.get_from_memory(self.session, title, category)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self._season_files_data_timestamps(
                    category, title.key
                )
                season = Season(
                    key=category,
                    name=MUSIC_CATEGORY_NAMES[category],
                    data_timestamp=max(data_timestamps),
                    title_id=title.id,
                ).upsert(title, season)
                # All updates are set by update_source.
                season.set_update_at(None)

            self._upsert_episodes(season, title.key, category, force=force)
            seasons.append(season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        category: CrunchyrollMusicCategory,
        *,
        force: bool = False,
    ) -> None:
        listing: Sequence[ConcertListingDatum | MusicVideoListingDatum] = (
            self.season_file(title_key, category).parsed().data
        )
        # Crunchyroll lists an artist's releases newest first, so the order is
        # reversed to number them the way they were released.
        for sort_order, datum in enumerate(reversed(listing)):
            episode_key = datum.id
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            details = self.concert_or_music_video_file(episode_key).parsed().data[0]
            data_timestamps = self._episode_files_data_timestamps(
                episode_key,
                season.key,
                title_key,
            )
            episode = Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=details.title,
                description=details.description,
                url=self.episode_url(category, episode_key),
                image_url=largest_image(details.images.thumbnail),
                thumbnail_url=nearest_thumbnail(details.images.thumbnail),
                duration=details.duration_ms // 1000,
                sort_order=sort_order,
                air_date=details.original_release,
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None)

    # TODO: Validate
    def browse_file(self) -> BrowseMusic:
        """BrowseMusic contains data for all of the music."""
        return self._cached_file(BrowseMusic, "artists")

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BrowseMusic]:
        return [self.browse_file()]

    # TODO: Validate
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible
            msg = "Title.url is not set."
            raise AttributeError(msg)

        for genre in self.artist_file(title.key).parsed().data[0].genres:
            self._add_urls_to_channel_by_prefix([title.url], genre.display_value)

    # TODO: Validate
    def create_channel_records(self) -> None:
        browse_file = self.browse_file()
        browse_file.download_if_outdated()
        self._add_urls_to_channel_by_prefix(
            [self.title_url(artist.id) for artist in browse_file.datums()],
            "All Music",
        )

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
    def update_source(self, source: Source, update_at: datetime) -> None:
        logger.info("Updating Source: {}", source.key)
        self._download_if_outdated(self._source_files(), update_at)
        artists = self.browse_file().datums()
        self.create_channel_records()
        self._mark_artists_as_outdated(artists)
        new_title_keys = {artist.id for artist in artists}
        self._mark_mismatched_titles_as_outdated(
            self.source_name(),
            new_title_keys,
            self._source_files_data_timestamps(),
        )
        self.upsert_source(self.source_name())
