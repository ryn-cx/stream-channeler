# TODO: Validate
"""What the plugin, its importers and its initializer all read YouTube by."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.sources.models import Source
from plugins.YouTube.basic_files import BasicFiles
from plugins.YouTube.constants import (
    FREE_SOURCE_KEY,
    LINKS_SOURCE_KEY,
    LONG_DOMAIN,
    PAID_SOURCE_KEY,
    SHORT_DOMAIN,
)
from plugins.YouTube.utils import (
    channel_uploads_playlist_key,
    get_first_item,
    is_an_album,
    is_channel_key,
    is_free_movies_channel,
    is_title_key,
    is_title_season_key,
    is_user_playlist,
    is_video_key,
    search_url,
    split_title_season_key,
    title_season_key,
    video_is_valid,
)
from plugins.YouTube.watch_history import WatchHistoryMixin

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from app.titles.models import Title
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class YouTubeShared(WatchHistoryMixin, BasicFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "YouTube"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return (
            "https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png"
        )

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        return [LONG_DOMAIN, SHORT_DOMAIN]

    # TODO: Validate
    @classmethod
    @override
    def link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_name(), FREE_SOURCE_KEY, PAID_SOURCE_KEY, LINKS_SOURCE_KEY)

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        existing_source = Source.get(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=source_key,
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=self._existing_data_timestamp_or_now(existing_source),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source

    # TODO: Validate
    def record_album_playlist_key(self, playlist_key: str) -> None:
        self._importing_album_playlist_key = playlist_key

    # TODO: Validate
    @override
    def soft_delete_missing_seasons(self, title_key: str) -> None:
        return

    # TODO: Validate
    @property
    def free_source(self) -> Source:
        return self._sources[FREE_SOURCE_KEY]

    # TODO: Validate
    @property
    def paid_source(self) -> Source:
        return self._sources[PAID_SOURCE_KEY]

    # TODO: Validate
    @property
    def links_source(self) -> Source:
        return self._sources[LINKS_SOURCE_KEY]

    # TODO: Validate
    def title_channel_key(self, title_key: str) -> str | None:
        # A title says nothing about who owns it, so what owns it is read off one of
        # its videos, every one of which is owned by whoever the title is.
        if is_channel_key(title_key):
            return title_key
        if is_video_key(title_key):
            episode_key = title_key
        else:
            episode_keys = self.title_episode_keys_from_files(title_key)
            if not episode_keys:
                return None
            episode_key = episode_keys[0]
        items = self.videos_file(episode_key).parsed().items
        return items[0].snippet.channel_id if items else None

    # TODO: Validate
    def is_free_movie(self, title_key: str) -> bool:
        channel_key = self.title_channel_key(title_key)
        return channel_key is not None and is_free_movies_channel(channel_key)

    # TODO: Validate
    def title_channel_title(self, title_key: str) -> str | None:
        episode_keys = self.title_episode_keys_from_files(title_key)
        if not episode_keys:
            return None
        items = self.videos_file(episode_keys[0]).parsed().items
        return items[0].snippet.channel_title if items else None

    # TODO: Validate
    def subscription_source(self, title_key: str) -> Source | None:
        if not is_title_key(title_key):
            return None
        if "Try now" not in self.title_listing_file_for_title(title_key).offer_labels():
            return None
        channel_title = self.title_channel_title(title_key)
        if not channel_title:
            return None

        source_key = f"{self.plugin_name()} {channel_title}"
        return self.upsert_source(source_key)

    # TODO: Validate
    def paid_or_free_source(self, title_key: str) -> Source:
        if subscription := self.subscription_source(title_key):
            return subscription
        if self.is_free_movie(title_key):
            return self.free_source
        return self.paid_source

    # TODO: Validate
    def tmdb_media_type(self, title_key: str) -> TMDBMediaType:
        return TMDBMediaType.movie if is_video_key(title_key) else TMDBMediaType.tv

    # TODO: Validate
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,  # noqa: ARG002 - Matches how every other file is asked for.
    ) -> int | None:
        if not (is_title_season_key(season_key) or is_an_album(season_key)):
            return None
        episode_keys = self._season_episode_keys_from_file(season_key)
        if episode_key not in episode_keys:
            return None
        return episode_keys.index(episode_key) + 1

    # TODO: Validate
    def _channel_has_only_uploads(self, title_key: str) -> bool:
        return self.channel_playlists_file(title_key).has_only_uploads()

    # TODO: Validate
    def _playlist_is_missing(self, title: Title, playlist_key: str) -> bool:
        # A URL for a whole title asks for every season it has, so nothing is missing
        # as long as it has been imported with seasons.
        if is_title_key(playlist_key) and not is_title_season_key(playlist_key):
            return not title.active_children

        # A URL for a Topic channel asks for every release the musician has, which
        # is the whole title, so nothing is missing once it has been imported with
        # seasons.
        if playlist_key == title.key and self.is_topic_channel(title.key):
            return not title.active_children

        # If the playlist being checked is the channel uploads playlist it should only
        # be considered missing if the channel has at least one upload.
        if playlist_key == channel_uploads_playlist_key(title.key):
            channel_by_channel_id = self.channel_by_channel_id_file(title.key)
            channel_item = get_first_item(channel_by_channel_id.parsed().items)
            if int(channel_item.statistics.video_count) == 0:
                return False
        return not Season.get_from_memory(self.session, title, playlist_key)

    # TODO: Validate
    def title_episode_keys_from_files(self, title_key: str) -> list[str]:
        """Return the episode keys of every season of a title, in season order."""
        return self._episode_keys_from_season_files(
            self._season_keys_from_title_files(title_key),
            title_key,
        )

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:  # noqa: PLR0911
        if is_video_key(title_key):
            return [self.videos_file(title_key)]
        if is_an_album(title_key):
            return [self.music_playlist_file(title_key)]
        if is_user_playlist(title_key):
            return [self.playlist_info_file(title_key)]
        # A title has no API of its own, so its page lists its seasons.
        if is_title_key(title_key):
            # The page comes first because it is what names the playlist the
            # listing is asked for by.
            return [
                self.title_page_file(title_key),
                self.title_listing_file_for_title(title_key),
            ]
        # A Topic channel's releases are the only thing it lists, and the API says
        # nothing about them, so they are read off the channel's page instead of
        # out of the playlists it owns.
        if self.is_topic_channel(title_key):
            return [
                self.topic_releases_file(title_key),
                self.channel_by_channel_id_file(title_key),
            ]
        # A channel generated for one title has no seasons but its uploads, so what
        # it lists is never read.
        if self.is_movies_channel(title_key):
            return [self.channel_by_channel_id_file(title_key)]
        return [
            # Required to detect new seasons (playlists).
            self.channel_playlists_file(title_key),
            # ChannelByHandle is only used to get ChannelByChannelId so it is not used.
            # Required to detect changes to the title (channel).
            self.channel_by_channel_id_file(title_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # A season that is a single video is described by the video itself.
        if is_video_key(season_key):
            return [self.videos_file(season_key)]
        # A season of a title is described by the page for that season.
        if is_title_season_key(season_key):
            title_key, _ = split_title_season_key(season_key)
            return [self.title_listing_file_for_title(title_key)]
        if is_an_album(season_key):
            return [self.music_playlist_file(season_key)]
        if is_user_playlist(title_key):
            return [
                self.playlist_items_file(season_key),
                self.playlist_info_file(title_key),
            ]
        return [
            # Required to detect new episodes (videos). Must stay first because
            # season_data_timestamp reads files[0].
            self.playlist_items_file(season_key),
            # Required to detect changes to the season (playlist).
            self.channel_playlists_file(title_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the episode (video).
        return [self.videos_file(episode_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        # A title that is a single video has that video as its only season.
        if is_video_key(title_key):
            return [title_key]

        if is_an_album(title_key) or is_user_playlist(title_key):
            return [title_key]

        # A title has one season for every season its page lists.
        if is_title_key(title_key):
            return [
                title_season_key(title_key, season_number)
                for season_number in self.title_season_numbers_from_file(title_key)
            ]

        # A Topic channel has one season for every release it lists.
        if self.is_topic_channel(title_key):
            return self._with_album_seasons(
                self.topic_release_keys_from_file(title_key),
                title_key,
            )

        channel_item = get_first_item(
            self.channel_by_channel_id_file(title_key).parsed().items,
        )
        season_keys: list[str] = []

        # If the channel has uploads also include that as a season. Generally, most
        # playlists consist of uploads from the channel so the channel should be the
        # first season_key listed so when the episodes are downloaded the channel
        # uploads are downloaded first because that will maximize the batch sizes and
        # minimize the number of API calls.
        if int(channel_item.statistics.video_count) > 0:
            season_keys.append(channel_uploads_playlist_key(title_key))

        # A channel generated for one title of YouTube's catalogue is that title and
        # nothing else, so what it uploaded is all of it and what it lists besides is
        # not the title.
        if self.is_movies_channel(title_key):
            return season_keys

        channel_playlists_file = self.channel_playlists_file(title_key)
        if channel_playlists_file.database_record.content:
            season_keys.extend(
                item.id
                for item in channel_playlists_file.parsed().items
                if item.content_details.item_count > 0
            )

        return self._with_album_seasons(season_keys, title_key)

    # TODO: Validate
    def _with_album_seasons(self, season_keys: list[str], title_key: str) -> list[str]:
        # An album playlist is auto-generated and listed by no channel, so it is only
        # ever added by an importing URL naming it and then always kept.
        return season_keys + [
            key
            for key in self._album_season_keys_from_database(title_key)
            if key not in season_keys
        ]

    # TODO: Validate
    def _album_season_keys_from_database(self, title_key: str) -> list[str]:
        season_keys: list[str] = []
        if self._importing_album_playlist_key:
            season_keys.append(self._importing_album_playlist_key)

        existing_title = self._preload_title(
            title_key,
            preload_seasons=True,
        ).one_or_none()
        if existing_title:
            season_keys.extend(
                season.key
                for season in existing_title.seasons
                if is_an_album(season.key) and season.key not in season_keys
            )
        return season_keys

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        # A channel generated for one title uploads that title once per language it
        # was published in, and every one of them is the same film, so the one
        # published here is the only one worth holding.
        usa_only = self.is_movies_channel(title_key)
        seen: set[str] = set()
        video_keys: list[str] = []
        for season_key in season_keys:
            for video_key in self._season_episode_keys_from_file(season_key):
                if video_key in seen:
                    continue
                if usa_only and not self.is_usa_video(video_key):
                    continue
                seen.add(video_key)
                video_keys.append(video_key)
        return video_keys

    # TODO: Validate
    def _season_episode_keys_from_file(self, season_key: str) -> list[str]:
        """Return the episode keys held by a single season."""
        # A season that is a single video holds only that video.
        if is_video_key(season_key):
            return [season_key]

        # A season of a title holds the episodes listed on its page.
        if is_title_season_key(season_key):
            title_key, season_number = split_title_season_key(season_key)
            episode_keys = self.title_listing_file_for_title(
                title_key,
            ).episode_keys_by_season()
            return episode_keys.get(int(season_number), [])

        if is_an_album(season_key):
            return self.music_playlist_file(season_key).track_keys()

        playlist_items_file = self.playlist_items_file(season_key)
        if not playlist_items_file.database_record.content:
            msg = (
                f"PlaylistItems file for season {season_key!r} has empty content "
                f"(file key {playlist_items_file.file_key()!r}, extra "
                f"{playlist_items_file.database_record.extra!r}). The playlist was "
                f"likely not found when downloaded."
            )
            raise ValueError(msg)
        return [
            item.content_details.video_id
            for item in playlist_items_file.parsed().items
            if video_is_valid(item.snippet.title)
        ]

    # TODO: Validate
    @override
    def _download_title_files_and_children(
        self,
        title_key: str,
        update_at: datetime | None = None,
    ) -> None:
        """Read the channel before the files that depend on what it is.

        Which files describe a channel is not the same for a Topic channel as for
        any other, and only the channel says which it is, so it is read before
        anything asks. Every video of every season is asked for in one batch
        rather than one at a time, since the API answers for fifty at once.
        """
        if is_channel_key(title_key):
            self.channel_by_channel_id_file(title_key).download_if_outdated(update_at)
        # The page names the playlist the title's listing is asked for by, so the
        # files a title has cannot be named until it has been read.
        if is_title_key(title_key):
            self.title_page_file(title_key).download_if_outdated(update_at)

        self._download_if_outdated(self._title_files(title_key), update_at)
        season_keys = self._season_keys_from_title_files(title_key)
        for season_key in season_keys:
            self._download_if_outdated(self._season_files(season_key, title_key))
        self._batch_download_missing_videos(
            self._episode_keys_from_season_files(season_keys, title_key),
        )
