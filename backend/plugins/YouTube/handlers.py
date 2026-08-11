# TODO: Validate
from __future__ import annotations

import re
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, override
from urllib.parse import parse_qs, urlparse

from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.url import URLHandler
from plugins.YouTube.files import (
    get_first_item,
    is_music_playlist_key,
    is_standalone_video_channel,
    is_video_key,
    show_season_key,
)

if TYPE_CHECKING:
    from app.shows.models import Show
    from plugins.utils.base_plugin.files import BaseFile
    from plugins.YouTube import YouTube
    from plugins.YouTube.files import (
        ChannelByChannelId,
        ChannelByHandle,
        ChannelByUsername,
    )


# TODO: Validate
def _single_video_import_results(
    show: Show,
    playlist_key: str,
    video_key: str,
) -> list[URLImportResult]:
    return [
        URLImportResult.for_episodes(
            show,
            [
                episode
                for season in show.seasons
                if season.key == playlist_key
                for episode in season.episodes
                if episode.key == video_key
            ],
        ),
    ]


# TODO: Validate
class YouTubeURLHandler(URLHandler["YouTube"]):
    # TODO: Validate
    def __init__(self, plugin: YouTube, url: str, match: re.Match[str]) -> None:
        self._match = match
        super().__init__(plugin, url)

    # TODO: Validate
    @classmethod
    def full_regex(cls, long_domain_regex: str, short_domain_regex: str) -> str:  # noqa: ARG003
        return long_domain_regex + cls._URL_REGEX

    # TODO: Validate
    @property
    @abstractmethod
    def playlist_key(self) -> str: ...

    # TODO: Validate
    @property
    def video_key(self) -> str | None:
        return None


# TODO: Validate
class VideoURLHandler(YouTubeURLHandler):
    # https://www.youtube.com/watch?v=jNQXAC9IVRw
    # https://www.youtube.com/shorts/jNQXAC9IVRw
    # https://youtu.be/jNQXAC9IVRw
    _URL_REGEX = r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&])"

    # TODO: Validate
    @classmethod
    @override
    def full_regex(cls, long_domain_regex: str, short_domain_regex: str) -> str:
        long_paths = rf"{long_domain_regex}\/(?:watch\?v=|shorts\/)"
        short_path = rf"{short_domain_regex}\/"
        return rf"(?:{long_paths}|{short_path})" + cls._URL_REGEX

    # TODO: Validate
    @property
    @override
    def video_key(self) -> str:
        return self._match.group("video_key")

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        videos_file = self.plugin.videos_file(self.video_key)
        channel_key = videos_file.parsed().items[0].snippet.channel_id
        # A channel that never lists this video cannot be imported to reach it, so the
        # video is imported as a show of its own instead.
        if is_standalone_video_channel(channel_key):
            return self.video_key
        return channel_key

    # TODO: Validate
    @property
    def playlist_key(self) -> str:
        show_key = self.show_key
        if is_video_key(show_key):
            return show_key
        return self.plugin.channel_uploads_playlist_key(show_key)

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.videos_file(self.video_key),
            self.url,
        )

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        return _single_video_import_results(show, self.playlist_key, self.video_key)


# TODO: Validate
class PlaylistBasedURLHandler(YouTubeURLHandler):
    # TODO: Validate
    @property
    @override
    def playlist_key(self) -> str:
        return self._match.group("playlist_key")

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        playlist_items_file = self.plugin.playlist_items_file(self.playlist_key)
        first_item = get_first_item(playlist_items_file.parsed().items)
        if is_music_playlist_key(self.playlist_key):
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

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.playlist_items_file(self.playlist_key),
            self.url,
        )


# TODO: Validate
class PlaylistURLHandler(PlaylistBasedURLHandler):
    # https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    _URL_REGEX = r"\/playlist\?list=(?P<playlist_key>(?:PL|OLAK5uy_)[^&]+)"

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        seasons = [season for season in show.seasons if season.key == self.playlist_key]
        return [URLImportResult.for_seasons(show, seasons)]


# TODO: Validate
class PlaylistVideoURLHandler(PlaylistBasedURLHandler):
    # https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    # https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    _URL_REGEX = (
        r"\/(?:watch\?v=)?(?P<video_key>[A-Za-z0-9_-]{11})[?&]"
        r"list=(?P<playlist_key>(?:PL|OLAK5uy_)[^&]+)"
    )

    # TODO: Validate
    @classmethod
    @override
    def full_regex(cls, long_domain_regex: str, short_domain_regex: str) -> str:
        return rf"(?:{long_domain_regex}|{short_domain_regex})" + cls._URL_REGEX

    # TODO: Validate
    @property
    @override
    def video_key(self) -> str:
        return self._match.group("video_key")

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        return _single_video_import_results(show, self.playlist_key, self.video_key)


# TODO: Validate
class ShowURLHandler(YouTubeURLHandler):
    # https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw
    # https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw?season=23&sbp=...
    _URL_REGEX = r"\/show\/(?P<show_key>SC[A-Za-z0-9_-]+?)(?:$|[/?])"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._match.group("show_key")

    # TODO: Validate
    @property
    def _season_number(self) -> str | None:
        """Return the season the URL asks for, or None when it asks for the show."""
        season = parse_qs(urlparse(self.url).query).get("season", [])
        return season[0] if season else None

    # TODO: Validate
    @property
    @override
    def playlist_key(self) -> str:
        season_number = self._season_number
        if season_number is None:
            return self.show_key
        return show_season_key(self.show_key, season_number)

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        show_page = self.plugin.show_page_file(self.show_key)
        self.plugin.raise_if_invalid_file(show_page, self.url)
        if not show_page.season_numbers():
            msg = f"Invalid {self.plugin.plugin_key()} URL: {self.url}"
            raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        # A URL for one season only asks for that season, where a URL for the show
        # asks for all of it.
        if self._season_number is None:
            return [URLImportResult.for_show(show)]
        seasons = [season for season in show.seasons if season.key == self.playlist_key]
        return [URLImportResult.for_seasons(show, seasons)]


# TODO: Validate
class ChannelURLHandler(YouTubeURLHandler):
    # TODO: Validate
    @property
    @abstractmethod
    def _channel_file(self) -> BaseFile[Any]:
        """Return the file that resolves the URL to a channel."""

    # TODO: Validate
    @property
    @override
    def playlist_key(self) -> str:
        return self.plugin.channel_uploads_playlist_key(self.show_key)

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(self._channel_file, self.url)

        # The channel only lists a fraction of the videos it owns, so importing it
        # would import almost none of them. Its videos are imported one at a time.
        if is_standalone_video_channel(self.show_key):
            msg = (
                f"{self.show_key} does not list most of the videos it owns, so import "
                f"the URL of an individual video instead of the channel: {self.url}"
            )
            raise InvalidURLError(msg)

    # TODO: Validate
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
        return [
            URLImportResult(
                show_identifier=show.show_identifier,
                season_identifiers=[season.season_identifier for season in seasons],
                is_whitelist=is_whitelist,
            ),
        ]


# TODO: Validate
class ChannelKeyURLHandler(ChannelURLHandler):
    # https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A
    _URL_REGEX = r"\/channel\/(?P<channel_key>UC.{22})(?:$|\/)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._match.group("channel_key")

    # TODO: Validate
    @property
    @override
    def _channel_file(self) -> ChannelByChannelId:
        return self.plugin.channel_by_channel_id_file(self.show_key)


# TODO: Validate
class ChannelUsernameURLHandler(ChannelURLHandler):
    # https://www.youtube.com/user/jawed
    _URL_REGEX = r"\/user\/(?P<channel_username>.+?)(?:$|\/)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return get_first_item(self._channel_file.parsed().items).id

    # TODO: Validate
    @property
    @override
    def _channel_file(self) -> ChannelByUsername:
        return self.plugin.channel_by_username_file(
            self._match.group("channel_username"),
        )


# TODO: Validate
class ChannelHandleURLHandler(ChannelURLHandler):
    # https://www.youtube.com/@jawed
    # https://www.youtube.com/c/jawed
    # https://www.youtube.com/jawed
    _URL_REGEX = r"\/(?:c\/|@)?(?P<channel_handle>.+?)(?:$|\/)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return get_first_item(self._channel_file.parsed().items).id

    # TODO: Validate
    @property
    @override
    def _channel_file(self) -> ChannelByHandle:
        return self.plugin.channel_by_handle_file(self._match.group("channel_handle"))
