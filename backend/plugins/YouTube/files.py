# TODO: Validate
import json
import time
from collections.abc import Sequence
from datetime import timedelta
from functools import cache
from typing import override

from get_around import GetAround
from loguru import logger
from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.channel import Channels as ChannelsEndpoint
from not_yt_dlapi.channel.models import ChannelModel
from not_yt_dlapi.playlist import Playlists as PlaylistsEndpoint
from not_yt_dlapi.playlist.models import PlaylistModel
from not_yt_dlapi.playlist_item import PlaylistItems as PlaylistItemsEndpoint
from not_yt_dlapi.playlist_item.models import PlaylistItemModel
from not_yt_dlapi.video.models import VideoModel
from sqlmodel import Session

from app.config import settings
from app.files.models import File
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    GAPIJSON,
    GAPIJSONNoGet,
    XMLFile,
)


@cache
def not_yt_dlapi() -> NotYTDLAPI:
    server: str | None = settings.GET_AROUND_SERVER
    if server == "changethis":
        server = None
    password: str | None = settings.GET_AROUND_PASSWORD
    if password == "changethis":  # noqa: S105
        password = None
    return NotYTDLAPI(
        settings.YOUTUBE_API_KEY,
        get_around_server=server,
        get_around_password=password,
    )


@cache
def get_around_client() -> GetAround:
    get_around_server: str | None = settings.GET_AROUND_SERVER
    if get_around_server == "changethis":
        get_around_server = None
    get_around_password: str | None = settings.GET_AROUND_PASSWORD
    if get_around_password == "changethis":  # noqa: S105
        get_around_password = None
    return GetAround(
        server=get_around_server,
        password=get_around_password,
    )


def get_first_item[T](items: list[T] | None) -> T:
    if not items:
        msg = "Expected at least one item, got none"
        raise ValueError(msg)
    return items[0]


class ChannelByChannelId(GAPIJSONNoGet[ChannelModel]):
    api_endpoint = not_yt_dlapi().channels

    @override
    def _get(self) -> ChannelModel:
        assert isinstance(self.api_endpoint, ChannelsEndpoint)  # noqa: S101
        return self.api_endpoint.get(channel_id=self.unique_identifier)

    @override
    def _get_acceptable_error(self) -> str:
        return f"Channel '{self.unique_identifier}' not found."


class ChannelByHandle(GAPIJSONNoGet[ChannelModel]):
    api_endpoint = not_yt_dlapi().channels

    @override
    def _get(self) -> ChannelModel:
        assert isinstance(self.api_endpoint, ChannelsEndpoint)  # noqa: S101
        return self.api_endpoint.get(handle=self.unique_identifier)

    @override
    def _get_acceptable_error(self) -> str:
        return f"Channel '{self.unique_identifier}' not found."


class ChannelByUsername(GAPIJSONNoGet[ChannelModel]):
    api_endpoint = not_yt_dlapi().channels

    @override
    def _get(self) -> ChannelModel:
        assert isinstance(self.api_endpoint, ChannelsEndpoint)  # noqa: S101
        return self.api_endpoint.get(username=self.unique_identifier)

    @override
    def _get_acceptable_error(self) -> str:
        return f"Channel '{self.unique_identifier}' not found."


class ChannelPlaylists(GAPIJSONNoGet[PlaylistModel]):
    api_endpoint = not_yt_dlapi().playlists

    @override
    def _get(self) -> PlaylistModel:
        assert isinstance(self.api_endpoint, PlaylistsEndpoint)  # noqa: S101
        return self.api_endpoint.get_all(self.unique_identifier)

    @override
    def _get_acceptable_error(self) -> str:
        return f"No playlists found for channel '{self.unique_identifier}'."


class PlaylistItems(GAPIJSONNoGet[PlaylistItemModel]):
    api_endpoint = not_yt_dlapi().playlist_items

    @override
    def _get(self) -> PlaylistItemModel:
        assert isinstance(self.api_endpoint, PlaylistItemsEndpoint)  # noqa: S101
        if not self._existing_database_record:
            return self.api_endpoint.get_all(self.unique_identifier)

        # If the entry is over a year old download a fresh copy to clean out deleted
        # videos.
        year_ago_datetime = tz_datetime.now() - timedelta(days=365)
        if self.parsed().not_yt_dlapi.timestamp < year_ago_datetime:
            return self.api_endpoint.get_all(self.unique_identifier)

        existing_items = self.parsed().items
        existing_ids = {item.content_details.video_id for item in existing_items}

        page = self.api_endpoint.get(self.unique_identifier)

        # TODO: noy_yt_dlapi needs to support fetching a specific page, until then
        # download all of the playlist videos if there are at least 50 new entries.
        if not any(
            item.content_details.video_id in existing_ids for item in page.items
        ):
            return self.api_endpoint.get_all(self.unique_identifier)

        new_ids = {item.content_details.video_id for item in page.items}
        page.items = list(page.items) + [
            item
            for item in existing_items
            if item.content_details.video_id not in new_ids
        ]
        return page

    @override
    def _get_acceptable_error(self) -> str:
        return "The playlist identified with the request's <code>playlistId</code> parameter cannot be found."


class Videos(GAPIJSON[VideoModel]):
    api_endpoint = not_yt_dlapi().videos


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
                msg = (
                    f"PlaylistFeed fetch for {self.unique_identifier} "
                    f"returned HTTP {response.status_code}"
                )
                raise RuntimeError(msg)
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

    def channel_by_channel_id_file(self, show_key: str) -> ChannelByChannelId:
        """Return a cached channel-by-channel-id file for the given show key."""
        return self._get_cached_file(
            ChannelByChannelId,
            show_key,
            lambda: ChannelByChannelId(self.session, self.plugin, show_key),
        )

    def channel_by_handle_file(self, channel_handle: str) -> ChannelByHandle:
        """Return a cached channel-by-handle file for the given channel handle."""
        return self._get_cached_file(
            ChannelByHandle,
            channel_handle,
            lambda: ChannelByHandle(self.session, self.plugin, channel_handle),
        )

    def channel_by_username_file(self, channel_username: str) -> ChannelByUsername:
        """Return a cached channel-by-username file for the given channel username."""
        return self._get_cached_file(
            ChannelByUsername,
            channel_username,
            lambda: ChannelByUsername(self.session, self.plugin, channel_username),
        )

    def channel_playlists_file(self, show_key: str) -> ChannelPlaylists:
        """Return a cached channel playlists file for the given show key."""
        return self._get_cached_file(
            ChannelPlaylists,
            show_key,
            lambda: ChannelPlaylists(self.session, self.plugin, show_key),
        )

    def playlist_items_file(self, season_key: str) -> PlaylistItems:
        """Return a cached playlist items file for the given season key."""
        return self._get_cached_file(
            PlaylistItems,
            season_key,
            lambda: PlaylistItems(self.session, self.plugin, season_key),
        )

    def videos_file(self, episode_key: str) -> Videos:
        """Return a cached videos file for the given episode key."""
        return self._get_cached_file(
            Videos,
            episode_key,
            lambda: Videos(self.session, self.plugin, episode_key),
        )

    def playlist_feed_file(self, season_key: str) -> PlaylistFeed:
        """Return a cached playlist feed file for the given season key."""
        return self._get_cached_file(
            PlaylistFeed,
            season_key,
            lambda: PlaylistFeed(self.session, self.plugin, season_key),
        )

    @override
    def _show_files(
        self,
        show_key: str,
    ) -> Sequence[ChannelByChannelId | ChannelPlaylists]:
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
    ) -> Sequence[ChannelPlaylists | PlaylistItems]:
        return [
            # Required to detect new episodes (videos).
            self.playlist_items_file(season_key),
            # Required to detect changes to the season (playlist).
            self.channel_playlists_file(show_key),
        ]

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
        channel_playlists_file = self.channel_playlists_file(show_key)
        season_keys: list[str] = []

        # If the channel has uploads also include that as a season. Generally, most
        # playlists consist of uploads from the channel so the channel should be the
        # first season_key listed so when the episodes are downloaded the channel
        # uploads are downloaded first because that will maximize the batch sizes and
        # minimize the number of API calls.
        item = get_first_item(self.channel_by_channel_id_file(show_key).parsed().items)
        if int(item.statistics.video_count) > 0:
            season_keys.append(self._get_channel_uploads_playlist_key(show_key))

        if channel_playlists_file.database_record.content:
            season_keys.extend(
                item.id
                for item in channel_playlists_file.parsed().items
                if item.content_details.item_count > 0
            )

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
        season_key: str,
        show_key: str,
    ) -> list[File]:
        """Batch download all videos for a season in a single API call."""
        video_keys = self._episode_keys_from_file(season_key)
        self._preload_episode_files(video_keys, season_key, show_key)

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
