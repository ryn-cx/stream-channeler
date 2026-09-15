# TODO: Validate
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, override

from loguru import logger

from app.episodes.models import Episode
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.Crunchyroll.constants import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    MUSIC_SOURCE,
    MUSIC_VIDEO_URL_REGEX,
    CrunchyrollMusicCategory,
)
from plugins.Crunchyroll.files import BrowseMusic
from plugins.Crunchyroll.importer import CrunchyrollImporter
from plugins.Crunchyroll.utils import (
    build_url,
    largest_image,
    nearest_thumbnail,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chirashi.artist_concerts.models import Datum as ConcertListingDatum
    from chirashi.artist_music_videos.models import Datum as MusicVideoListingDatum
    from chirashi.browse_music.models import Datum as BrowseMusicDatum

    from plugins.utils.base_plugin.files import BaseFile

MUSIC_CATEGORY_NAMES = {
    CrunchyrollMusicCategory.CONCERT: "Concerts",
    CrunchyrollMusicCategory.MUSIC_VIDEO: "Music Videos",
}


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
    def _link_to_tmdb(cls) -> bool:
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
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        for url_regex, group in (
            (MUSIC_VIDEO_URL_REGEX, "music_video_key"),
            (CONCERT_URL_REGEX, "concert_key"),
        ):
            if match := re.match(domain_regex + url_regex, url):
                episode_key = match.group(group)
                music_file = self.concert_or_music_video_file(episode_key)
                self.raise_invalid_url_if_no_content(music_file, url)
                return ParsedURL(
                    music_file.parsed().artist.id,
                    episode_key=episode_key,
                )

        if match := re.match(domain_regex + ARTIST_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.artist_file(title_key), url)
            return ParsedURL(title_key)

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
            artist_data = self.artist_file(title_key).parsed()
            title = Title(
                key=title_key,
                name=artist_data.name,
                description=artist_data.description,
                media_type="Music",
                url=self.title_url(title_key),
                image_url=largest_image(artist_data.images.poster_wide),
                thumbnail_url=nearest_thumbnail(artist_data.images.poster_wide),
                data_timestamp=self._title_files_data_timestamp(title_key),
                tmdb_title_validated_at=tz_datetime.now(),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(
                    title_key,
                    min(self._title_files_data_timestamps(title_key)),
                ),
            )

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        seasons: list[Season] = []
        for category in CrunchyrollMusicCategory:
            season = Season.get_from_memory(self.session, title, category)
            if self._season_is_outdated(season, title.key, force=force):
                season = Season(
                    key=category,
                    name=MUSIC_CATEGORY_NAMES[category],
                    data_timestamp=self._season_files_data_timestamp(
                        category,
                        title.key,
                    ),
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
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                details = self.concert_or_music_video_file(episode_key).parsed()
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
                    data_timestamp=self._episode_files_data_timestamp(
                        episode_key,
                        season.key,
                        title_key,
                    ),
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
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible
            msg = "Title.url is not set."
            raise AttributeError(msg)

        channel_keys = ["All Music"]
        channel_keys.extend(
            genre.display_value for genre in self.artist_file(title.key).parsed().genres
        )
        for channel_key in channel_keys:
            self.add_new_urls_to_channel(channel_key, [title.url])

    # TODO: Validate
    def create_channel_records(self) -> None:
        browse_file = self.browse_file()
        browse_file.download_if_outdated()
        self.add_new_urls_to_channel(
            "All Music",
            [self.title_url(artist.id) for artist in browse_file.datums()],
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
