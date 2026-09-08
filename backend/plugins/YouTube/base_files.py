# TODO: Validate
from __future__ import annotations

from plugins.utils.base_plugin.base import BasePlugin
from plugins.YouTube.files import (
    # Browse,
    ChannelByChannelId,
    ChannelPlaylists,
    MusicPlaylist,
    PlaylistFeed,
    # PlaylistInfo,
    PlaylistItems,
    Topic,
    Videos,
)


# TODO: Validate
class YouTubeBaseFiles(BasePlugin):
    # TODO: Validate
    def channel_by_channel_id_file(self, title_key: str) -> ChannelByChannelId:
        return self._cached_file(ChannelByChannelId, title_key)

    # TODO: Validate
    def channel_playlists_file(self, title_key: str) -> ChannelPlaylists:
        return self._cached_file(ChannelPlaylists, title_key)

    # TODO: Validate
    # def playlist_info_file(self, playlist_key: str) -> PlaylistInfo:
    #     return self._cached_file(PlaylistInfo, playlist_key)

    # TODO: Validate
    def playlist_items_file(self, season_key: str) -> PlaylistItems:
        return self._cached_file(PlaylistItems, season_key)

    # TODO: Validate
    def videos_file(self, episode_key: str) -> Videos:
        return self._cached_file(Videos, episode_key)

    # TODO: Validate
    def playlist_feed_file(self, season_key: str) -> PlaylistFeed:
        return self._cached_file(PlaylistFeed, season_key)

    # TODO: Validate
    # def browse_file(self, title_key: str) -> Browse:
    #     return self._cached_file(Browse, title_key)

    # TODO: Validate
    def music_playlist_file(self, playlist_key: str) -> MusicPlaylist:
        return self._cached_file(MusicPlaylist, playlist_key)

    # TODO: Validate
    def topic_file(self, channel_key: str) -> Topic:
        return self._cached_file(Topic, channel_key)
