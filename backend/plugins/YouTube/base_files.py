# TODO: Validate
from __future__ import annotations

from plugins.utils.base_plugin.base import BasePlugin
from plugins.YouTube.files import (
    Browse,
    ChannelByChannelId,
    ChannelByHandle,
    ChannelByUsername,
    ChannelPlaylists,
    MusicPlaylist,
    PlaylistFeed,
    PlaylistInfo,
    PlaylistItems,
    Topic,
    Videos,
)


# TODO: Validate
class YouTubeBaseFiles(BasePlugin):
    _importing_album_playlist_key: str | None = None

    def channel_by_channel_id_file(self, title_key: str) -> ChannelByChannelId:
        return self._file(ChannelByChannelId, title_key)

    def channel_by_handle_file(self, channel_handle: str) -> ChannelByHandle:
        return self._file(ChannelByHandle, channel_handle)

    def channel_by_username_file(self, channel_username: str) -> ChannelByUsername:
        return self._file(ChannelByUsername, channel_username)

    def channel_playlists_file(self, title_key: str) -> ChannelPlaylists:
        return self._file(ChannelPlaylists, title_key)

    def playlist_info_file(self, playlist_key: str) -> PlaylistInfo:
        return self._file(PlaylistInfo, playlist_key)

    def playlist_items_file(self, season_key: str) -> PlaylistItems:
        return self._file(PlaylistItems, season_key)

    def videos_file(self, episode_key: str) -> Videos:
        return self._file(Videos, episode_key)

    def playlist_feed_file(self, season_key: str) -> PlaylistFeed:
        return self._file(PlaylistFeed, season_key)

    def browse_file(self, title_key: str) -> Browse:
        return self._file(Browse, title_key)

    def music_playlist_file(self, playlist_key: str) -> MusicPlaylist:
        return self._file(MusicPlaylist, playlist_key)

    def topic_file(self, channel_key: str) -> Topic:
        return self._file(Topic, channel_key)
