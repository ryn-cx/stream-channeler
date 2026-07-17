# TODO: Validate
import json
import time
from collections.abc import Sequence
from datetime import timedelta
from functools import cache
from typing import override

from loguru import logger
from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.channel import Channels as ChannelsEndpoint
from not_yt_dlapi.channel.models import ChannelsModel
from not_yt_dlapi.playlist.models import PlaylistModel
from not_yt_dlapi.playlist_item import PlaylistItems as PlaylistItemsEndpoint
from not_yt_dlapi.playlist_item.models import PlaylistItemsModel
from not_yt_dlapi.playlists import Playlists as PlaylistsEndpoint
from not_yt_dlapi.playlists.models import PlaylistsModel
from not_yt_dlapi.video.models import VideosModel
from sqlmodel import Session

from app.config import settings
from app.files.models import File
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    GAPIJSON,
    GAPIJSONNoGet,
    XMLFile,
)
from plugins.utils.get_around_client import get_around_client


@cache
def not_yt_dlapi() -> NotYTDLAPI:
    return NotYTDLAPI(
        settings.YOUTUBE_API_KEY,
        get_around_client=get_around_client(),
    )


def get_first_item[T](items: list[T] | None) -> T:
    if not items:
        msg = "Expected at least one item, got none"
        raise ValueError(msg)
    return items[0]


class ChannelByChannelId(GAPIJSONNoGet[ChannelsModel]):
    API_ENDPOINT = not_yt_dlapi().channels

    @override
    def _get(self) -> ChannelsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, ChannelsEndpoint)
        return endpoint.get(channel_id=self.unique_identifier)

    @override
    def _get_ACCEPTABLE_ERROR(self) -> str:
        return f"Channel '{self.unique_identifier}' not found."


class ChannelByHandle(GAPIJSONNoGet[ChannelsModel]):
    API_ENDPOINT = not_yt_dlapi().channels

    @override
    def _get(self) -> ChannelsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, ChannelsEndpoint)
        return endpoint.get(handle=self.unique_identifier)

    @override
    def _get_ACCEPTABLE_ERROR(self) -> str:
        return f"Channel '{self.unique_identifier}' not found."


class ChannelByUsername(GAPIJSONNoGet[ChannelsModel]):
    API_ENDPOINT = not_yt_dlapi().channels

    @override
    def _get(self) -> ChannelsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, ChannelsEndpoint)
        return endpoint.get(username=self.unique_identifier)

    @override
    def _get_ACCEPTABLE_ERROR(self) -> str:
        return f"Channel '{self.unique_identifier}' not found."


class ChannelPlaylists(GAPIJSONNoGet[PlaylistsModel]):
    API_ENDPOINT = not_yt_dlapi().playlists

    @override
    def _get(self) -> PlaylistsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, PlaylistsEndpoint)
        return endpoint.get_all(self.unique_identifier)

    @override
    def _get_ACCEPTABLE_ERROR(self) -> str:
        return f"No playlists found for channel '{self.unique_identifier}'."


class PlaylistInfo(GAPIJSON[PlaylistModel]):
    API_ENDPOINT = not_yt_dlapi().playlist


class PlaylistItems(GAPIJSONNoGet[PlaylistItemsModel]):
    API_ENDPOINT = not_yt_dlapi().playlist_items

    # Due to API limits this function merges new videos with existing videos instead of
    # downloading all videos every time.
    @override
    def _get(self) -> PlaylistItemsModel:
        endpoint = self.raise_if_not_is_instance(
            self.API_ENDPOINT,
            PlaylistItemsEndpoint,
        )

        # If this is the first time downloading the file download everything.
        if not self._existing_database_record:
            return endpoint.get_all(self.unique_identifier)

        # If the entry is over a year old download a fresh copy to clean out deleted
        # videos.
        year_ago_datetime = tz_datetime.now() - timedelta(days=365)
        if self._existing_database_record.data_timestamp < year_ago_datetime:
            return endpoint.get_all(self.unique_identifier)

        existing_items = self.parsed().items
        existing_video_ids = {item.content_details.video_id for item in existing_items}

        page = endpoint.get(self.unique_identifier)

        # TODO: noy_yt_dlapi needs to support fetching a specific page, until then
        # download all of the playlist videos if there are at least 50 new entries.
        if not any(
            item.content_details.video_id in existing_video_ids for item in page.items
        ):
            return endpoint.get_all(self.unique_identifier)

        new_ids = {item.content_details.video_id for item in page.items}
        page.items = list(page.items) + [
            item
            for item in existing_items
            if item.content_details.video_id not in new_ids
        ]
        return page

    @override
    def _get_ACCEPTABLE_ERROR(self) -> str:
        return "The playlist identified with the request's <code>playlistId</code> parameter cannot be found."


class Videos(GAPIJSON[VideosModel]):
    API_ENDPOINT = not_yt_dlapi().videos


class PlaylistFeed(XMLFile):
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            if self.unique_identifier.startswith("UU"):
                params = {"channel_id": "UC" + self.unique_identifier[2:]}
            else:
                params = {"playlist_id": self.unique_identifier}
            response = get_around_client().get(
                "https://www.youtube.com/feeds/videos.xml",
                params=params,
            )
            if not response.is_success:
                logger.warning(
                    "PlaylistFeed fetch for {} returned HTTP {}; keeping the existing feed.",
                    self.unique_identifier,
                    response.status_code,
                )
                return
            self.write(response.text)

    def video_ids(self) -> list[str]:
        namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        result: list[str] = []
        for entry in self.parsed().findall("atom:entry", namespaces):
            video_id = entry.find("yt:videoId", namespaces)
            if video_id is not None and video_id.text:
                result.append(video_id.text)
        return result


class FileMixin(BasePlugin, register=False):
    @override
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self._imported_album_playlist_keys: set[str] = set()

    def channel_by_channel_id_file(self, show_key: str) -> ChannelByChannelId:
        """Return a cached ChannelByChannelId for the given show key."""
        return self._get_cached_file(
            ChannelByChannelId,
            show_key,
            lambda: ChannelByChannelId(self.session, self.plugin, show_key),
        )

    def channel_by_handle_file(self, channel_handle: str) -> ChannelByHandle:
        """Return a cached ChannelByHandle for the given channel handle."""
        return self._get_cached_file(
            ChannelByHandle,
            channel_handle,
            lambda: ChannelByHandle(self.session, self.plugin, channel_handle),
        )

    def channel_by_username_file(self, channel_username: str) -> ChannelByUsername:
        """Return a cached ChannelByUsername for the given channel username."""
        return self._get_cached_file(
            ChannelByUsername,
            channel_username,
            lambda: ChannelByUsername(self.session, self.plugin, channel_username),
        )

    def channel_playlists_file(self, show_key: str) -> ChannelPlaylists:
        """Return a cached ChannelPlaylists for the given show key."""
        return self._get_cached_file(
            ChannelPlaylists,
            show_key,
            lambda: ChannelPlaylists(self.session, self.plugin, show_key),
        )

    def playlist_info_file(self, playlist_key: str) -> PlaylistInfo:
        """Return a cached PlaylistInfo for the given playlist key."""
        return self._get_cached_file(
            PlaylistInfo,
            playlist_key,
            lambda: PlaylistInfo(self.session, self.plugin, playlist_key),
        )

    def playlist_items_file(self, season_key: str) -> PlaylistItems:
        """Return a cached PlaylistItems for the given season key."""
        return self._get_cached_file(
            PlaylistItems,
            season_key,
            lambda: PlaylistItems(self.session, self.plugin, season_key),
        )

    def videos_file(self, episode_key: str) -> Videos:
        """Return a cached Videos for the given episode key."""
        return self._get_cached_file(
            Videos,
            episode_key,
            lambda: Videos(self.session, self.plugin, episode_key),
        )

    def playlist_feed_file(self, season_key: str) -> PlaylistFeed:
        """Return a cached PlaylistFeed for the given season key."""
        return self._get_cached_file(
            PlaylistFeed,
            season_key,
            lambda: PlaylistFeed(self.session, self.plugin, season_key),
        )

    @staticmethod
    def _is_music_playlist_key(key: str) -> bool:
        return key.startswith("OLAK5uy_")

    def _channel_has_only_uploads(self, show_key: str) -> bool:
        channel_playlists_file = self.channel_playlists_file(show_key)
        if not channel_playlists_file.database_record.content:
            return True
        return not any(
            item.content_details.item_count > 0
            for item in channel_playlists_file.parsed().items
        )

    @override
    def _show_files(
        self,
        show_key: str,
    ) -> Sequence[ChannelByChannelId | ChannelPlaylists | PlaylistItems]:
        return [
            # Required to detect new seasons (playlists).
            self.channel_playlists_file(show_key),
            # ChannelByHandle is only used to get ChannelByChannelId so it is not used.
            # Required to detect changes to the show (channel).
            self.channel_by_channel_id_file(show_key),
        ]

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[ChannelPlaylists | PlaylistItems | PlaylistInfo]:
        files: list[ChannelPlaylists | PlaylistItems | PlaylistInfo] = [
            # Required to detect new episodes (videos). Must stay first because
            # season_data_timestamp reads files[0].
            self.playlist_items_file(season_key),
            # Required to detect changes to the season (playlist).
            self.channel_playlists_file(show_key),
        ]
        # Album playlists are auto-generated and not listed by the channel, so the album
        # name comes from the playlist itself rather than the channel playlists file.
        if self._is_music_playlist_key(season_key):
            files.append(self.playlist_info_file(season_key))
        return files

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[Videos]:
        # Required to detect changes to the episode (video).
        return [self.videos_file(episode_key)]

    def _video_is_valid(self, video_title: str) -> bool:
        """Check if a video is valid for importing."""
        return video_title not in ("Deleted video", "Private video")

    def _get_channel_uploads_playlist_key(self, show_key: str) -> str:
        """Return the playlist ID for the channel's uploads."""
        return show_key[:1] + "U" + show_key[2:]

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        channel_item = get_first_item(
            self.channel_by_channel_id_file(show_key).parsed().items,
        )
        season_keys: list[str] = []

        # If the channel has uploads also include that as a season. Generally, most
        # playlists consist of uploads from the channel so the channel should be the
        # first season_key listed so when the episodes are downloaded the channel
        # uploads are downloaded first because that will maximize the batch sizes and
        # minimize the number of API calls.
        if int(channel_item.statistics.video_count) > 0:
            season_keys.append(self._get_channel_uploads_playlist_key(show_key))

        channel_playlists_file = self.channel_playlists_file(show_key)
        if channel_playlists_file.database_record.content:
            season_keys.extend(
                item.id
                for item in channel_playlists_file.parsed().items
                if item.content_details.item_count > 0
            )

        # Album playlists are auto-generated and not returned by any channel listing, so
        # they are only ever added by an explicit import and then always kept.
        season_keys.extend(
            key for key in self._album_season_keys(show_key) if key not in season_keys
        )

        return season_keys

    def _album_season_keys(self, show_key: str) -> list[str]:
        season_keys: list[str] = list(self._imported_album_playlist_keys)
        existing_show = self._preload_show(
            show_key,
            preload_seasons=True,
        ).one_or_none()
        if existing_show:
            for season in existing_show.seasons:
                if (
                    season.deleted_at is None
                    and self._is_music_playlist_key(season.key)
                    and season.key not in season_keys
                ):
                    season_keys.append(season.key)
        return season_keys

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        seen: set[str] = set()
        video_keys: list[str] = []
        for season_key in season_keys:
            playlist_items_file = self.playlist_items_file(season_key)
            for item in playlist_items_file.parsed().items:
                video_id = item.content_details.video_id
                if self._video_is_valid(item.snippet.title) and video_id not in seen:
                    seen.add(video_id)
                    video_keys.append(video_id)
        return video_keys

    @override
    def _download_all_episode_files(
        self,
        season: str | Season,
        show: str | Show | None = None,
        preloaded_files: Sequence[File] | None = None,
    ) -> list[File]:
        """Batch download all videos for a season in a single API call."""
        season_key = self._key(season)
        show_key = self._show_key(season, show)
        video_keys = self._episode_keys_from_file(season_key)
        self._preload_episode_files(video_keys, season_key, show_key, preloaded_files)

        outdated_ids = [
            video_id
            for video_id in video_keys
            if self.videos_file(video_id).is_outdated()
        ]

        if outdated_ids:
            logger.info(f"Batch downloading {len(outdated_ids)} videos")
            start = time.monotonic()
            responses = not_yt_dlapi().videos.download_multiple(outdated_ids)
            elapsed_time = time.monotonic() - start
            logger.info(
                f"Batch downloaded {len(outdated_ids)} videos in {elapsed_time:.2f}s",
            )

            for video_id, response in zip(outdated_ids, responses, strict=True):
                video_file = self.videos_file(video_id)
                # write is called directly because of the way the files are batch downloaded.
                video_file.write(json.dumps(response, default=str))

        return [self.videos_file(video_id).database_record for video_id in video_keys]
