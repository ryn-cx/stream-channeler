# TODO: Validate
from __future__ import annotations

from plugins.utils.base_plugin.base import BasePlugin
from plugins.YouTube.constants import LONG_DOMAIN, SHORT_DOMAIN
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

    # TODO: Validate
    @classmethod
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            cls._playlist_video_url_regex(),  # Must be first due to regex overlap
            # cls._title_playlist_url_regex(),
            cls._playlist_url_regex(),
            cls._video_url_regex(),
            cls._channel_key_url_regex(),
            # cls._title_url_regex(),
            cls._channel_username_url_regex(),
            cls._channel_handle_url_regex(),
        )

    # TODO: Validate
    @classmethod
    def _playlist_video_url_regex(cls) -> str:
        # https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        # https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        return (
            cls._domains_regex([LONG_DOMAIN, SHORT_DOMAIN])
            + r"\/(?:watch\?v=)?(?P<video_key>[A-Za-z0-9_-]{11})[?&]"
            r"list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
        )

    # TODO: Validate
    # @classmethod
    # def _title_playlist_url_regex(cls) -> str:
    #     # https://www.youtube.com/playlist?list=TVSHX2-tv9KBHSAWLsDbH3h9vNzwxEAyyqXMw
    #     return cls._domain_regex([LONG_DOMAIN]) + (
    #         r"\/playlist\?list=(?P<title_playlist_key>TVSH[^&]+)"
    #     )

    # TODO: Validate
    @classmethod
    def _playlist_url_regex(cls) -> str:
        # https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        return cls._domains_regex([LONG_DOMAIN]) + (
            r"\/playlist\?list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
        )

    # TODO: Validate
    @classmethod
    def _video_url_regex(cls) -> str:
        # https://www.youtube.com/watch?v=jNQXAC9IVRw
        # https://www.youtube.com/shorts/jNQXAC9IVRw
        # https://youtu.be/jNQXAC9IVRw
        long_domain = cls._domains_regex([LONG_DOMAIN])
        short_domain = cls._domains_regex([SHORT_DOMAIN])
        return (
            rf"(?:{long_domain}\/(?:watch\?v=|shorts\/)|{short_domain}\/)"
            r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&])"
        )

    # TODO: Validate
    @classmethod
    def _channel_key_url_regex(cls) -> str:
        # https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A
        return cls._domains_regex([LONG_DOMAIN]) + (
            r"\/channel\/(?P<channel_key>UC.{22})(?:$|\/)"
        )

    # TODO: Validate
    # @classmethod
    # def _title_url_regex(cls) -> str:
    #     # https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw
    #     # https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw?season=23&sbp=...
    #     return cls._domain_regex([LONG_DOMAIN]) + (
    #         r"\/show\/(?P<title_key>SC[A-Za-z0-9_-]+?)(?:$|[/?])"
    #     )

    # TODO: Validate
    @classmethod
    def _channel_username_url_regex(cls) -> str:
        # https://www.youtube.com/user/jawed
        return cls._domains_regex([LONG_DOMAIN]) + (
            r"\/user\/(?P<channel_username>.+?)(?:$|\/)"
        )

    # TODO: Validate
    @classmethod
    def _channel_handle_url_regex(cls) -> str:
        # https://www.youtube.com/@jawed
        # https://www.youtube.com/c/jawed
        # https://www.youtube.com/jawed
        return cls._domains_regex([LONG_DOMAIN]) + (
            r"\/(?:c\/|@)?(?P<channel_handle>.+?)(?:$|\/)"
        )
