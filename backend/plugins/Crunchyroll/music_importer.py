# TODO: Validate
from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils import tz_datetime
from plugins.Crunchyroll.constants import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    MUSIC_SOURCE,
    MUSIC_VIDEO_URL_REGEX,
    CrunchyrollMusicCategory,
)
from plugins.Crunchyroll.files import (
    Artist,
    ArtistConcerts,
    ArtistMusicVideos,
    Concert,
    MusicVideo,
)
from plugins.Crunchyroll.shared import (
    CATEGORY_ID_PREFIXES,
    CrunchyrollShared,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.upserter import BaseUpserter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from chirashi.artist_concerts.models import Datum as ConcertListingDatum
    from chirashi.artist_music_videos.models import Datum as MusicVideoListingDatum

    from plugins.Crunchyroll.shared import CrunchyrollSizedImage
    from plugins.utils.base_plugin.files import BaseFile

MUSIC_CATEGORY_NAMES = {
    CrunchyrollMusicCategory.CONCERT: "Concerts",
    CrunchyrollMusicCategory.MUSIC_VIDEO: "Music Videos",
}


# TODO: Validate
class CrunchyrollMusicShared(CrunchyrollShared, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MUSIC_VIDEO_URL_REGEX, CONCERT_URL_REGEX, ARTIST_URL_REGEX)

    # TODO: Validate
    @classmethod
    @override
    def source_name(cls) -> str:
        return MUSIC_SOURCE

    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"artist/{title_key}")


# TODO: Validate
class CrunchyrollMusicFiles(CrunchyrollMusicShared, BaseUpserter, ABC):
    # TODO: Validate
    @staticmethod
    def music_episode_category(episode_key: str) -> CrunchyrollMusicCategory:
        """Return the listing an episode is a video or a concert of."""
        return CATEGORY_ID_PREFIXES[episode_key[:2]]

    # TODO: Validate
    def artist_file(self, artist_id: str) -> Artist:
        return self._cached_file(Artist, artist_id)

    # TODO: Validate
    def artist_music_videos_file(self, artist_id: str) -> ArtistMusicVideos:
        return self._cached_file(ArtistMusicVideos, artist_id)

    # TODO: Validate
    def artist_concerts_file(self, artist_id: str) -> ArtistConcerts:
        return self._cached_file(ArtistConcerts, artist_id)

    # TODO: Validate
    def music_video_file(self, music_video_id: str) -> MusicVideo:
        return self._cached_file(MusicVideo, music_video_id)

    # TODO: Validate
    def concert_file(self, concert_id: str) -> Concert:
        return self._cached_file(Concert, concert_id)

    # TODO: Validate
    def season_file(
        self,
        artist_id: str,
        category: CrunchyrollMusicCategory,
    ) -> ArtistMusicVideos | ArtistConcerts:
        """Return the ArtistMusicVideos or ArtistConcerts file based on the category.

        Each artist (Title) has two `Season`s, one for concerts and one for music
        videos. This function main purpose is to make sure the correct files are
        returned when getting all of the files for a specific season.
        """
        if category is CrunchyrollMusicCategory.CONCERT:
            return self.artist_concerts_file(artist_id)
        return self.artist_music_videos_file(artist_id)

    # TODO: Validate
    def concert_or_music_video_file(
        self,
        episode_key: str,
    ) -> MusicVideo | Concert:
        """Return the Concert or MusicVideo file based on the category.

        There are different files for concerts and music videos. This function main
        purpose is to make sure the correct files are returned when getting all of the
        files for a specific episode.
        """
        if self.music_episode_category(episode_key) is CrunchyrollMusicCategory.CONCERT:
            return self.concert_file(episode_key)
        return self.music_video_file(episode_key)

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
class CrunchyrollMusicChannels(CrunchyrollMusicFiles, ABC):
    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible
            msg = "Title.url is not set."
            raise AttributeError(msg)

        genres = self.artist_file(title.key).parsed().genres
        self.add_title_to_channel("All Music", title)
        self.set_title_tag_channels(title, [genre.display_value for genre in genres])


# TODO: Validate
class CrunchyrollMusicUpsert(CrunchyrollMusicChannels, ABC):
    # TODO: Validate
    @classmethod
    def episode_url(cls, category: CrunchyrollMusicCategory, episode_key: str) -> str:
        return cls.build_url(f"watch/{category}/{episode_key}")

    # TODO: Validate
    @staticmethod
    def largest_image(images: Sequence[CrunchyrollSizedImage]) -> str | None:
        """Return the source of the widest size Crunchyroll offers an image in."""
        if not images:
            return None
        return max(images, key=lambda image: image.width).source

    # TODO: Validate
    @override
    def _update_and_upsert_title(self, title: Title) -> None:
        artist_file = self.artist_file(title.key)
        self._download_if_outdated([artist_file], title.update_at)
        if artist_file.record_content is None:
            title.soft_delete()
            self.remove_title_from_plugin_channels(title)
            return
        super()._update_and_upsert_title(title)

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        artist_data = self.artist_file(title_key).parsed()
        upserted_title = Title(
            key=title_key,
            name=artist_data.name,
            description=artist_data.description,
            media_type=MediaType.music,
            url=self.title_url(title_key),
            image_url=self.largest_image(artist_data.images.poster_wide),
            thumbnail_url=self.nearest_thumbnail(artist_data.images.poster_wide),
            data_timestamp=self._title_files_data_timestamp(title_key),
            tmdb_title_validated_at=tz_datetime.now(),
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(
            genre.display_value for genre in artist_data.genres
        )

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        seasons: list[Season] = []
        for category in CrunchyrollMusicCategory:
            existing_season = Season.get_from_memory(self.session, title, category)
            upserted_season = Season(
                key=category,
                name=MUSIC_CATEGORY_NAMES[category],
                data_timestamp=self._season_files_data_timestamp(
                    category,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key, category)
            self._set_season_update_at(upserted_season)
            for datum in self.season_file(title.key, category).parsed().data:
                upserted_season.set_update_at(datum.availability.end_date)
            seasons.append(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        category: CrunchyrollMusicCategory,
    ) -> None:
        listing: Sequence[ConcertListingDatum | MusicVideoListingDatum] = (
            self.season_file(title_key, category).parsed().data
        )
        # Crunchyroll lists an artist's releases newest first, so the order is
        # reversed to number them the way they were released.
        for sort_order, datum in enumerate(reversed(listing)):
            episode_key = datum.id
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            details = self.concert_or_music_video_file(episode_key).parsed()
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=details.title,
                description=details.description,
                url=self.episode_url(category, episode_key),
                image_url=self.largest_image(details.images.thumbnail),
                thumbnail_url=self.nearest_thumbnail(details.images.thumbnail),
                duration=details.duration_ms // 1000,
                sort_order=sort_order,
                air_date=details.original_release,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class CrunchyrollMusicImporter(CrunchyrollMusicUpsert):
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
