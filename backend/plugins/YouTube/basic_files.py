# TODO: Validate
from __future__ import annotations

import json
import time
from typing import Any

from loguru import logger

from plugins.utils.base_plugin.base import BasePlugin
from plugins.YouTube.files import (
    ChannelByChannelId,
    ChannelByHandle,
    ChannelByUsername,
    ChannelPlaylists,
    MusicPlaylist,
    PlaylistFeed,
    PlaylistInfo,
    PlaylistItems,
    ShowListing,
    ShowPage,
    TopicReleases,
    Videos,
    not_yt_dlapi,
)
from plugins.YouTube.utils import is_an_album, is_channel_key


# TODO: Validate
class BasicFiles(BasePlugin):
    _importing_album_playlist_key: str | None = None

    # TODO: Validate
    def channel_by_channel_id_file(self, show_key: str) -> ChannelByChannelId:
        return self._file(ChannelByChannelId, show_key)

    # TODO: Validate
    def channel_by_handle_file(self, channel_handle: str) -> ChannelByHandle:
        return self._file(ChannelByHandle, channel_handle)

    # TODO: Validate
    def channel_by_username_file(self, channel_username: str) -> ChannelByUsername:
        return self._file(ChannelByUsername, channel_username)

    # TODO: Validate
    def channel_playlists_file(self, show_key: str) -> ChannelPlaylists:
        return self._file(ChannelPlaylists, show_key)

    # TODO: Validate
    def playlist_info_file(self, playlist_key: str) -> PlaylistInfo:
        return self._file(PlaylistInfo, playlist_key)

    # TODO: Validate
    def playlist_items_file(self, season_key: str) -> PlaylistItems:
        return self._file(PlaylistItems, season_key)

    # TODO: Validate
    def videos_file(self, episode_key: str) -> Videos:
        return self._file(Videos, episode_key)

    # TODO: Validate
    def playlist_feed_file(self, season_key: str) -> PlaylistFeed:
        return self._file(PlaylistFeed, season_key)

    # TODO: Validate
    def show_page_file(self, show_key: str) -> ShowPage:
        return self._file(ShowPage, show_key)

    # TODO: Validate
    def show_listing_file(self, show_playlist_key: str) -> ShowListing:
        return self._file(ShowListing, show_playlist_key)

    # TODO: Validate
    def music_playlist_file(self, playlist_key: str) -> MusicPlaylist:
        return self._file(MusicPlaylist, playlist_key)

    # TODO: Validate
    def topic_releases_file(self, channel_key: str) -> TopicReleases:
        return self._file(TopicReleases, channel_key)

    # TODO: Validate
    def show_playlist_key(self, show_key: str) -> str:
        # Browse lists a show under the playlist it is published as rather than
        # under the key its page is served at, and only the page says which that
        # is.
        playlist_key = self.show_page_file(show_key).playlist_key()
        if playlist_key is None:
            msg = f"The page for show {show_key!r} names no playlist to list it by."
            raise ValueError(msg)
        return playlist_key

    # TODO: Validate
    def show_listing_file_for_show(self, show_key: str) -> ShowListing:
        return self.show_listing_file(self.show_playlist_key(show_key))

    # TODO: Validate
    def is_topic_channel(self, show_key: str) -> bool:
        """Report whether a channel key belongs to a musician's Topic channel.

        Only the channel says so, and this reads what has been downloaded rather
        than downloading it, so a channel that has not been read yet is answered
        for as the plain channel it is taken for until it has been.
        """
        if not is_channel_key(show_key):
            return False

        channel_file = self.channel_by_channel_id_file(show_key)
        if channel_file.is_outdated() or not channel_file.database_record.content:
            return False
        items = channel_file.parsed().items
        if not items:
            return False
        return items[0].snippet.title.endswith(" - Topic")

    # TODO: Validate
    def is_movies_channel(self, show_key: str) -> bool:
        if not is_channel_key(show_key):
            return False

        channel_file = self.channel_by_channel_id_file(show_key)
        if channel_file.is_outdated() or not channel_file.database_record.content:
            return False
        items = channel_file.parsed().items
        if not items:
            return False
        return items[0].snippet.title == "YouTube Movies"

    # TODO: Validate
    def is_usa_video(self, video_key: str) -> bool:
        # A video that has not been read yet is taken to be one, since what says
        # otherwise is the video itself and reading it is what this decides.
        videos_file = self.videos_file(video_key)
        if videos_file.is_outdated() or not videos_file.database_record.content:
            return True

        items = videos_file.parsed().items
        if not items:
            return False
        restriction = items[0].content_details.region_restriction
        if restriction is None or restriction.allowed is None:
            return False
        return "US" in restriction.allowed

    # TODO: Validate
    def topic_release_keys_from_file(self, channel_key: str) -> list[str]:
        """Return the playlist key of every release a Topic channel lists."""
        return [
            release_key
            for release_key in self.topic_releases_file(channel_key).release_keys()
            if is_an_album(release_key)
        ]

    # TODO: Validate
    def show_season_numbers_from_file(self, show_key: str) -> list[str]:
        return [
            str(number)
            for number in self.show_listing_file_for_show(show_key).season_numbers()
        ]

    # TODO: Validate
    def _batch_download_missing_videos(self, video_keys: list[str]) -> None:
        outdated_ids = [
            video_id
            for video_id in video_keys
            if self.videos_file(video_id).is_outdated()
        ]
        if not outdated_ids:
            return

        logger.info(f"Batch downloading {len(outdated_ids)} YouTube videos")
        start = time.monotonic()
        responses = not_yt_dlapi().videos.download_all(outdated_ids)
        elapsed_time = time.monotonic() - start
        logger.info(
            f"Batch downloaded {len(outdated_ids)} YouTube videos "
            f"in {elapsed_time:.2f}s",
        )

        # A batch answers for fifty videos at once and every video is stored in a
        # file of its own, so each item is written out as the response it would
        # have arrived in had it been asked for on its own.
        responses_by_id: dict[str, str] = {}
        for response in responses:
            page: dict[str, Any] = json.loads(response)
            for item in page["items"]:
                responses_by_id[item["id"]] = json.dumps({**page, "items": [item]})
        for video_id in outdated_ids:
            video_file = self.videos_file(video_id)
            # write is called directly because of the way the files are batch
            # downloaded.
            video_file.write(responses_by_id[video_id])
