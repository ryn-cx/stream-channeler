# TODO: Validate
from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.utils import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    EPISODE_URL_REGEX,
    MUSIC_CATEGORY_NAMES,
    MUSIC_SOURCE,
    MUSIC_VIDEO_URL_REGEX,
    SERIES_URL_REGEX,
    MusicCategory,
    artist_url,
    episode_image,
    episode_thumbnail,
    episode_url,
    largest_image,
    nearest_thumbnail,
    series_url,
    show_image,
    show_thumbnail,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin_v3.importer import BaseImporter
from plugins.utils.base_plugin_v3.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chirashi.artist_concerts.models import Datum as ConcertListingDatum
    from chirashi.artist_music_videos.models import Datum as MusicVideoListingDatum

    from app.sources.models import Source
    from plugins.utils.base_plugin_v3.files import BaseFile


# TODO: Validate
class CrunchyrollMedia(CrunchyrollShared, BaseImporter, ABC):
    pass


# TODO: Validate
class CrunchyrollSeries(CrunchyrollMedia):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    @override
    def _url_source(self) -> Source:
        return self.video_source

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            show_key = match.group("show_key")
            self.raise_if_invalid_file(self.series_file(show_key), url)
            return MediaInfo(show_key)

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            return self._episode_media_info(match.group("episode_key"), url)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _episode_media_info(self, episode_key: str, url: str) -> MediaInfo:
        objects_file = self.objects_file(episode_key)
        self.raise_if_invalid_file(objects_file, url)

        # Episodes for different regions have different keys. The show is always
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
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        series_data = self._series_datum(show_key)
        return [
            TMDBLookupInfo(
                series_data.title,
                TMDBMediaType.movie if self._is_movie(show_key) else TMDBMediaType.tv,
                series_data.series_launch_year,
            ),
        ]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new seasons.
            self.seasons_file(show_key),
            # Required to detect changes to the show.
            self.series_file(show_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new episodes.
            self.season_episodes_file(season_key),
            # Required to detect changes to the season.
            self.seasons_file(show_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.season_episodes_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            season_data.id for season_data in self.seasons_file(show_key).parsed().data
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
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
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            series_data = self._series_datum(show_key)
            data_timestamps = self.show_data_timestamps(show_key)
            new_show = Show(
                key=series_data.id,
                name=series_data.title,
                description=series_data.description,
                media_type="Movie" if self._is_movie(show_key) else "Series",
                url=series_url(series_data.id),
                image_url=show_image(series_data.images),
                thumbnail_url=show_thumbnail(series_data.images),
                year=series_data.series_launch_year,
                data_timestamp=data_timestamps[0],
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_seasons(show, force=force)
        self._soft_delete_missing(show_key)
        self._set_weekly_updates_from_episodes(show)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        seasons_file = self.seasons_file(show.key)
        for sort_order, season_data in enumerate(seasons_file.parsed().data):
            season = Season.get_from_memory(self.session, show, season_data.id)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_data.id, show.key)
                new_season = Season(
                    key=season_data.id,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    sort_order=sort_order,
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, show.key, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episodes_data = self.season_episodes_file(season.key).parsed()
        for sort_order, episode_data in enumerate(episodes_data.data):
            episode = Episode.get_from_memory(self.session, season, episode_data.id)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                episode_data.id,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=episode_data.id,
                watch_identifier=watch_identifier(self.plugin_name(), episode_data.id),
                name=episode_data.title,
                episode_number=episode_data.episode_number,
                url=episode_url(episode_data.id),
                description=episode_data.description,
                image_url=episode_image(episode_data.images),
                thumbnail_url=episode_thumbnail(episode_data.images),
                duration=episode_data.duration_ms // 1000,
                sort_order=sort_order,
                air_date=episode_data.episode_air_date,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class CrunchyrollArtist(CrunchyrollMedia):
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
            show_key = match.group("artist_key")
            self.raise_if_invalid_file(self.artist_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect changes to the artist.
            self.artist_file(show_key),
            # Required to detect new music videos and concerts.
            self.artist_music_videos_file(show_key),
            self.artist_concerts_file(show_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new music videos or concerts.
            self.artist_concerts_or_artist_music_videos_file(
                show_key,
                MusicCategory(season_key),
            ),
            # Required to detect changes to the artist.
            self.artist_file(show_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # A music video or concert carries its own details, unlike a series
        # episode which is read out of its season's listing.
        return [self.concert_or_music_video_file(episode_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        # Both categories are always seasons of the artist, even while one is
        # empty, so a first release into it is a new episode rather than a
        # new season the show has to notice.
        return [category.value for category in MusicCategory]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            datum.id
            for season_key in season_keys
            for datum in self.artist_concerts_or_artist_music_videos_file(
                show_key,
                MusicCategory(season_key),
            )
            .parsed()
            .data
        ]

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            artist_data = self.artist_file(show_key).parsed().data[0]
            data_timestamps = self.show_data_timestamps(show_key)
            new_show = Show(
                key=show_key,
                name=artist_data.name,
                description=artist_data.description,
                media_type="Music",
                url=artist_url(show_key),
                image_url=largest_image(artist_data.images.poster_wide),
                thumbnail_url=nearest_thumbnail(artist_data.images.poster_wide),
                data_timestamp=data_timestamps[0],
                canonical_show_validated_at=tz_datetime.now(),
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_seasons(show, force=force)
        self._soft_delete_missing(show_key)

        return show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        for category in MusicCategory:
            season = Season.get_from_memory(self.session, show, category)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(category, show.key)
                season = Season(
                    key=category,
                    name=MUSIC_CATEGORY_NAMES[category],
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                ).upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, show.key, category, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        category: MusicCategory,
        *,
        force: bool = False,
    ) -> None:
        listing: Sequence[ConcertListingDatum | MusicVideoListingDatum] = (
            self.artist_concerts_or_artist_music_videos_file(show_key, category)
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
                show_key,
                force=force,
            ):
                continue

            details = self.concert_or_music_video_file(episode_key).parsed().data[0]
            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                show_key,
            )
            episode = Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=details.title,
                description=details.description,
                url=episode_url(episode_key),
                image_url=largest_image(details.images.thumbnail),
                thumbnail_url=nearest_thumbnail(details.images.thumbnail),
                duration=details.duration_ms // 1000,
                sort_order=sort_order,
                air_date=details.original_release,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            ).upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
