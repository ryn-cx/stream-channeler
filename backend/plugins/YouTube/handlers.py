# TODO: Validate
from __future__ import annotations

import re
from abc import abstractmethod
from typing import TYPE_CHECKING, override

from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.url import URLHandler
from plugins.YouTube.files import get_first_item

if TYPE_CHECKING:
    from app.shows.models import Show
    from plugins.YouTube import YouTube


def _single_video_import_results(
    show: Show,
    playlist_key: str,
    video_key: str,
) -> list[URLImportResult]:
    return [
        URLImportResult(
            show=show,
            episodes=[
                episode
                for season in show.seasons
                if season.key == playlist_key
                for episode in season.episodes
                if episode.key == video_key
            ],
            is_whitelist=True,
        ),
    ]


class YouTubeURLHandler(URLHandler["YouTube"]):
    def __init__(self, plugin: YouTube, url: str, match: re.Match[str]) -> None:
        self._match = match
        super().__init__(plugin, url)

    @classmethod
    def full_regex(cls, long_domain_regex: str, short_domain_regex: str) -> str:  # noqa: ARG003
        return long_domain_regex + cls._URL_REGEX

    @property
    @abstractmethod
    def playlist_key(self) -> str: ...

    @property
    def video_key(self) -> str | None:
        return None


class VideoURLHandler(YouTubeURLHandler):
    # https://www.youtube.com/watch?v=jNQXAC9IVRw
    # https://www.youtube.com/shorts/jNQXAC9IVRw
    # https://youtu.be/jNQXAC9IVRw
    _URL_REGEX = r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&])"

    @classmethod
    @override
    def full_regex(cls, long_domain_regex: str, short_domain_regex: str) -> str:
        long_paths = rf"{long_domain_regex}\/(?:watch\?v=|shorts\/)"
        short_path = rf"{short_domain_regex}\/"
        return rf"(?:{long_paths}|{short_path})" + cls._URL_REGEX

    @property
    @override
    def video_key(self) -> str:
        return self._match.group("video_key")

    @property
    @override
    def show_key(self) -> str:
        videos_file = self.plugin.videos_file(self.video_key)
        return videos_file.parsed().items[0].snippet.channel_id

    @property
    def playlist_key(self) -> str:
        return self.plugin.channel_uploads_playlist_key(self.show_key)

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.videos_file(self.video_key),
            self.url,
        )

    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        return _single_video_import_results(show, self.playlist_key, self.video_key)


class PlaylistBasedURLHandler(YouTubeURLHandler):
    @property
    @override
    def playlist_key(self) -> str:
        return self._match.group("playlist_key")

    @property
    @override
    def show_key(self) -> str:
        playlist_items_file = self.plugin.playlist_items_file(self.playlist_key)
        first_item = get_first_item(playlist_items_file.parsed().items)
        if self.plugin.is_music_playlist_key(self.playlist_key):
            # Automatically generated music playlists have a
            # first_item.snippet.channel_id value of UCBR8-60-B28hp2BmDPdntcQ which is
            # the official YouTube channel
            # https://www.youtube.com/channel/UCBR8-60-B28hp2BmDPdntcQ
            # first_item.snippet.video_owner_channel_id will link to the YouTube Topic
            # channel which actually owns the playlist.
            owner_channel_id = first_item.snippet.video_owner_channel_id
            if not owner_channel_id:
                msg = f"Playlist {self.playlist_key} is missing video_owner_channel_id."
                raise ValueError(msg)
            self.plugin.record_album_playlist_key(self.playlist_key)
            return owner_channel_id
        return first_item.snippet.channel_id

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.playlist_items_file(self.playlist_key),
            self.url,
        )


class PlaylistURLHandler(PlaylistBasedURLHandler):
    # https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    _URL_REGEX = r"\/playlist\?list=(?P<playlist_key>(?:PL|OLAK5uy_)[^&]+)"

    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        seasons = [season for season in show.seasons if season.key == self.playlist_key]
        return [URLImportResult(show=show, seasons=seasons, is_whitelist=True)]


class PlaylistVideoURLHandler(PlaylistBasedURLHandler):
    # https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    # https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    _URL_REGEX = (
        r"\/(?:watch\?v=)?(?P<video_key>[A-Za-z0-9_-]{11})[?&]"
        r"list=(?P<playlist_key>(?:PL|OLAK5uy_)[^&]+)"
    )

    @classmethod
    @override
    def full_regex(cls, long_domain_regex: str, short_domain_regex: str) -> str:
        return rf"(?:{long_domain_regex}|{short_domain_regex})" + cls._URL_REGEX

    @property
    @override
    def video_key(self) -> str:
        return self._match.group("video_key")

    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        return _single_video_import_results(show, self.playlist_key, self.video_key)


class ChannelURLHandler(YouTubeURLHandler):
    @property
    @override
    def playlist_key(self) -> str:
        return self.plugin.channel_uploads_playlist_key(self.show_key)

    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        seasons = [season for season in show.seasons if season.key == self.playlist_key]
        is_whitelist = True
        # TODO: I do not like this if logic and variable name.
        uploads_key = self.plugin.channel_uploads_playlist_key(show.key)
        show_season_keys = {season.key for season in show.seasons}
        # If the URL ends with playlists or a channel has no uploads return all of the
        # playlists for the channel.
        if self.url.endswith("/playlists") or uploads_key not in show_season_keys:
            is_whitelist = False
            seasons = list(show.seasons)
        return [URLImportResult(show=show, seasons=seasons, is_whitelist=is_whitelist)]


class ChannelKeyURLHandler(ChannelURLHandler):
    # https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A
    _URL_REGEX = r"\/channel\/(?P<channel_key>UC.{22})(?:$|\/)"

    @property
    @override
    def show_key(self) -> str:
        return self._match.group("channel_key")

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.channel_by_channel_id_file(self.show_key),
            self.url,
        )


class ChannelUsernameURLHandler(ChannelURLHandler):
    # https://www.youtube.com/user/jawed
    _URL_REGEX = r"\/user\/(?P<channel_username>.+?)(?:$|\/)"

    @property
    @override
    def show_key(self) -> str:
        username_file = self.plugin.channel_by_username_file(
            self._match.group("channel_username"),
        )
        return get_first_item(username_file.parsed().items).id

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.channel_by_username_file(
                self._match.group("channel_username"),
            ),
            self.url,
        )


class ChannelHandleURLHandler(ChannelURLHandler):
    # https://www.youtube.com/@jawed
    # https://www.youtube.com/c/jawed
    # https://www.youtube.com/jawed
    _URL_REGEX = r"\/(?:c\/|@)?(?P<channel_handle>.+?)(?:$|\/)"

    @property
    @override
    def show_key(self) -> str:
        handle_file = self.plugin.channel_by_handle_file(
            self._match.group("channel_handle"),
        )
        return get_first_item(handle_file.parsed().items).id

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.channel_by_handle_file(self._match.group("channel_handle")),
            self.url,
        )
