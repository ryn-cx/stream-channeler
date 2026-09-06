# TODO: Validate
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, override

from loguru import logger

from app.canonical_media.keys import watch_identifier
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.episodes.models import Episode
from app.files.models import File
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.Crunchyroll.files import BrowseMusic, BrowseSeries
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.utils import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    EPISODE_URL_REGEX,
    MUSIC_CATEGORY_NAMES,
    MUSIC_SOURCE,
    MUSIC_VIDEO_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_SOURCE,
    CrunchyrollMusicCategory,
    build_url,
    episode_image,
    episode_thumbnail,
    is_movie,
    largest_image,
    nearest_thumbnail,
    tenant_category_name,
    title_image,
    title_thumbnail,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.files import COMPLETED_STATUS, INITIAL_FILE_IDENTIFIER
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from chirashi.artist_concerts.models import Datum as ConcertListingDatum
    from chirashi.artist_music_videos.models import Datum as MusicVideoListingDatum
    from chirashi.browse_series.models import Datum as BrowseSeriesDatum

    from app.channels.models import Channel
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
        data_timestamp = self.source_data_timestamp()
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=source_key,
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(data_timestamp + self._source_update_interval())
        return source


# TODO: Validate
class CrunchyrollAnimeImporter(CrunchyrollImporter):
    """Plugin for handling Crunchyroll anime and live-action series.

    Named CrunchyRollAnime because the majority of the titles it handles will be anime
    and this name makes it as clear as possible that it does not import music content.
    """

    __categories_by_title_key: dict[str, list[str]] | None = None

    # TODO: Validate
    @classmethod
    @override
    def _source_update_interval(cls) -> timedelta:
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
    def _url_source(self) -> Source:
        return self._sources[VIDEO_SOURCE]

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_if_invalid_file(self.series_file(title_key), url)
            return MediaInfo(title_key)

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            return self._episode_media_info(match.group("episode_key"), url)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _episode_media_info(self, episode_key: str, url: str) -> MediaInfo:
        objects_file = self.objects_file(episode_key)
        self.raise_if_invalid_file(objects_file, url)

        # Episodes for different regions have different keys. The title is always
        # imported for the original region so the episode key also needs to match.
        for version in objects_file.parsed().data[0].episode_metadata.versions:
            if version.original:
                episode_key = version.guid
                break

        original_file = self.objects_file(episode_key)
        self.raise_if_invalid_file(original_file, url)
        return MediaInfo(
            original_file.parsed().data[0].episode_metadata.series_id,
            episode_key=episode_key,
        )

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        series_data = self.series_file(title_key).parsed().data[0]
        return [
            TMDBLookupInfo(
                series_data.title,
                TMDBMediaType.movie if is_movie(series_data) else TMDBMediaType.tv,
                series_data.series_launch_year,
            ),
        ]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new seasons.
            self.seasons_file(title_key),
            # Required to detect changes to the title.
            self.series_file(title_key),
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
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            series_data = self.series_file(title_key).parsed().data[0]
            data_timestamp = self.title_data_timestamp(title_key)
            new_title = Title(
                key=series_data.id,
                name=series_data.title,
                description=series_data.description,
                media_type="Movie" if is_movie(series_data) else "Series",
                url=self.title_url(series_data.id),
                image_url=title_image(series_data.images),
                thumbnail_url=title_thumbnail(series_data.images),
                year=series_data.series_launch_year,
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(None, data_timestamp)

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing(title_key)
        self._set_weekly_updates_from_episodes(title)
        self.link_title_to_tmdb(title)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        seasons_file = self.seasons_file(title.key)
        for sort_order, season_data in enumerate(seasons_file.parsed().data):
            season = Season.get_from_memory(self.session, title, season_data.id)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamp = self.season_data_timestamp(season_data.id, title.key)
                new_season = Season(
                    key=season_data.id,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    sort_order=sort_order,
                    data_timestamp=data_timestamp,
                    title_id=title.id,
                )
                season = new_season.upsert(title, season)
                season.set_update_at(None, data_timestamp)

            self._upsert_episodes(season, title.key, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        episodes_data = self.season_episodes_file(season.key).parsed()
        for sort_order, episode_data in enumerate(episodes_data.data):
            episode = Episode.get_from_memory(self.session, season, episode_data.id)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            data_timestamp = self.episode_data_timestamp(
                episode_data.id,
                season.key,
                title_key,
            )
            new_episode = Episode(
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
                data_timestamp=data_timestamp,
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamp)

    # TODO: Validate
    def browse_file(
        self,
        browse: datetime | File | Literal["Initial"],
    ) -> BrowseSeries:
        """Return data for recently aired titles."""
        if isinstance(browse, File):
            return self._file(
                BrowseSeries,
                BrowseSeries.file_to_unique_identifier(browse),
            )
        return self._file(BrowseSeries, str(browse))

    # TODO: Validate
    def find_newest_browse_file(self) -> BrowseSeries | None:
        """Return newest browse series file or None if one does not exist."""
        if file := self.preload_latest_file(BrowseSeries):
            return self.browse_file(file)
        return None

    # TODO: Validate
    def newest_browse_file(self) -> BrowseSeries:
        if file := self.find_newest_browse_file():
            return file
        initial = self.browse_file(INITIAL_FILE_IDENTIFIER)
        initial.download_if_outdated()
        return initial

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BrowseSeries]:
        """Return the `Source` files for Crunchyroll video."""
        return [self.newest_browse_file()]

    # TODO: Validate
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:
            msg = "Title.url is not set."
            raise AttributeError(msg)

        for tenant_category in self._categories_by_title_key().get(title.key, []):
            category_name = tenant_category_name(tenant_category)
            self.add_urls_to_plugin_channel(
                f"{VIDEO_SOURCE} - {category_name}",
                f"**Every {category_name} series on Crunchyroll.**",
                [title.url],
            )

    # TODO: Validate
    def _categories_by_title_key(self) -> dict[str, list[str]]:
        if self.__categories_by_title_key is None:
            categories_by_title_key: dict[str, list[str]] = {}
            for datum in self.catalogue_file().data():
                categories_by_title_key[datum.id] = list(
                    datum.series_metadata.tenant_categories,
                )
            self.__categories_by_title_key = categories_by_title_key
        return self.__categories_by_title_key

    # TODO: Validate
    def _plugin_channel(self) -> Channel:
        """Return the plugin owned channel every Crunchyroll series is queued into."""
        return self.add_urls_to_plugin_channel(
            VIDEO_SOURCE,
            "**Every anime from Crunchyroll in a single location.**",
        )

    # TODO: Validate
    def create_channel_records(self) -> None:
        _cache = self._preload_sources(VIDEO_SOURCE, preload_seasons=True).all()
        self._create_channel_records_from_file(self.catalogue_file().data())
        for browse_json in self.get_incomplete_files(
            BrowseSeries,
            self.browse_file,
        ):
            self._create_channel_records_from_file(browse_json.datums())
            browse_json.database_record.status = COMPLETED_STATUS

    # TODO: Validate
    def _create_channel_records_from_file(
        self,
        releases: list[BrowseSeriesDatum],
    ) -> None:
        new_series_urls = [
            self.title_url(release.id)
            for release in releases
            if not Title.get_from_memory(
                self.session,
                self._sources[VIDEO_SOURCE],
                release.id,
            )
        ]
        if new_series_urls:
            add_urls_to_channel_import_queue(
                self.session,
                self._plugin_channel(),
                new_series_urls,
            )

    # TODO: Validate
    def _mark_series_as_outdated(self, releases: list[BrowseSeriesDatum]) -> None:
        _cache = self._preload_sources(VIDEO_SOURCE, preload_seasons=True).all()
        for release in releases:
            if title := Title.get_from_memory(
                self.session,
                self._sources[VIDEO_SOURCE],
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
        self.create_channel_records()
        releases = [*self.catalogue_file().data(), *browse_file.datums()]
        self._mark_series_as_outdated(releases)
        self._mark_mismatched_titles_as_outdated(
            {release.id for release in releases},
            source_key=VIDEO_SOURCE,
        )
        self.upsert_source(VIDEO_SOURCE)


# TODO: Validate
class CrunchyrollMusicImporter(CrunchyrollImporter):
    # Check weekly for new music because updates do not need to be frequent.
    # TODO: Validate
    @classmethod
    @override
    def _source_update_interval(cls) -> timedelta:
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
        return (
            MUSIC_VIDEO_URL_REGEX,  # Must be listed first due to URL overlap.
            CONCERT_URL_REGEX,
            ARTIST_URL_REGEX,
        )

    # TODO: Validate
    @override
    def _url_source(self) -> Source:
        return self._sources[MUSIC_SOURCE]

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()
        for url_regex, group in (
            (MUSIC_VIDEO_URL_REGEX, "music_video_key"),
            (CONCERT_URL_REGEX, "concert_key"),
        ):
            if match := re.match(domain_regex + url_regex, url):
                episode_key = match.group(group)
                music_file = self.concert_or_music_video_file(episode_key)
                self.raise_if_invalid_file(music_file, url)
                return MediaInfo(
                    music_file.parsed().data[0].artist.id,
                    episode_key=episode_key,
                )

        if match := re.match(domain_regex + ARTIST_URL_REGEX, url):
            title_key = match.group("artist_key")
            self.raise_if_invalid_file(self.artist_file(title_key), url)
            return MediaInfo(title_key)

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
            self.artist_concerts_or_artist_music_videos_file(
                title_key,
                CrunchyrollMusicCategory(season_key),
            ),
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
            for datum in self.artist_concerts_or_artist_music_videos_file(
                title_key,
                CrunchyrollMusicCategory(season_key),
            )
            .parsed()
            .data
        ]

    # TODO: Validate
    @override
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            artist_data = self.artist_file(title_key).parsed().data[0]
            data_timestamp = self.title_data_timestamp(title_key)
            new_title = Title(
                key=title_key,
                name=artist_data.name,
                description=artist_data.description,
                media_type="Music",
                url=self.title_url(title_key),
                image_url=largest_image(artist_data.images.poster_wide),
                thumbnail_url=nearest_thumbnail(artist_data.images.poster_wide),
                data_timestamp=data_timestamp,
                canonical_title_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(None, data_timestamp)

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
                data_timestamp = self.season_data_timestamp(category, title.key)
                season = Season(
                    key=category,
                    name=MUSIC_CATEGORY_NAMES[category],
                    data_timestamp=data_timestamp,
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None, data_timestamp)

            self._upsert_episodes(season, title.key, category, force=force)
            seasons.append(season)

        self._set_season_update_at_based_on_last_episode(seasons[-1])

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
            self.artist_concerts_or_artist_music_videos_file(title_key, category)
            .parsed()
            .data
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
            data_timestamp = self.episode_data_timestamp(
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
                data_timestamp=data_timestamp,
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None, data_timestamp)

    # TODO: Validate
    def browse_file(self) -> BrowseMusic:
        """Return data for all of the music."""
        return self._file(BrowseMusic, "artists")

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BrowseMusic]:
        """Return the `Source` files for Crunchyroll music."""
        return [self.browse_file()]

    # TODO: Validate
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:
            msg = "Title.url is not set."
            raise AttributeError(msg)

        for genre in self.artist_file(title.key).parsed().data[0].genres:
            self.add_urls_to_plugin_channel(
                f"{MUSIC_SOURCE} - {genre.display_value}",
                f"**Every {genre.display_value} artist on Crunchyroll.**",
                [title.url],
            )

    # TODO: Validate
    @staticmethod
    def _channel_description() -> str:
        return (Path(__file__).parent / "music_channel_description.md").read_text(
            encoding="utf-8",
        )

    # TODO: Validate
    def _plugin_channel(self) -> Channel:
        """Return the plugin owned channel every Crunchyroll artist is queued into."""
        return self.add_urls_to_plugin_channel(
            MUSIC_SOURCE,
            self._channel_description(),
        )

    # TODO: Validate
    def create_channel_records(self) -> None:
        artists = self.browse_file().datums()
        _cache = self._preload_sources(MUSIC_SOURCE, preload_seasons=True).all()
        new_artist_urls: list[str] = []
        for artist in artists:
            if title := Title.get_from_memory(
                self.session,
                self._sources[MUSIC_SOURCE],
                artist.id,
            ):
                # It's easier to update the title and the artists at the same time.
                title.set_update_at(artist.updated_at)
                for season in title.seasons:
                    season.set_update_at(artist.updated_at)
            else:
                new_artist_urls.append(self.title_url(artist.id))

        add_urls_to_channel_import_queue(
            self.session,
            self._plugin_channel(),
            new_artist_urls,
        )

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        logger.info("Updating Source: {}", source.name)
        # This is the only source file so no source_files wrapper is needed.
        self.browse_file().download_if_outdated(update_at)
        self.create_channel_records()
        self._mark_mismatched_titles_as_outdated(
            {artist.id for artist in self.browse_file().datums()},
            source_key=MUSIC_SOURCE,
        )
        self.upsert_source(MUSIC_SOURCE)
