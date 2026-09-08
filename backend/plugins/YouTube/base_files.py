from __future__ import annotations

from plugins.utils.base_plugin.base import BasePlugin
from plugins.YouTube.files import (
    Browse,
    ChannelByChannelId,
    ChannelPlaylists,
    MusicPlaylist,
    PlaylistFeed,
    PlaylistInfo,
    PlaylistItems,
    Topic,
    Videos,
)


class YouTubeBaseFiles(BasePlugin):
    def channel_by_channel_id_file(self, title_key: str) -> ChannelByChannelId:
        return self._file(ChannelByChannelId, title_key)

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
