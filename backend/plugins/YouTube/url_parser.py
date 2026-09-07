# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from plugins.utils.abstract_plugin import InvalidURLError
from plugins.YouTube.constants import (
    CHANNEL_HANDLE_URL_REGEX,
    CHANNEL_KEY_URL_REGEX,
    CHANNEL_USERNAME_URL_REGEX,
    PLAYLIST_URL_REGEX,
    PLAYLIST_VIDEO_URL_REGEX,
    TITLE_PLAYLIST_URL_REGEX,
    TITLE_URL_REGEX,
    VIDEO_URL_REGEX,
)
from plugins.YouTube.utils import (
    channel_key_from_uploads_playlist_key,
    channel_uploads_playlist_key,
    get_first_item,
    is_an_album,
    is_channel_uploads_playlist_key,
    is_free_movies_channel,
    is_topic_channel,
    is_video_key,
    title_season_key,
    title_season_numbers_from_file,
)

if TYPE_CHECKING:
    from not_yt_dlapi.channels.models import ChannelsModel

    from plugins.utils.base_plugin.files import BaseFile
    from plugins.YouTube.shared import YouTubeShared


# TODO: Validate
class YouTubeURLParser:
    title_key: str
    playlist_key: str
    video_key: str | None
    whole_title: bool
    musician_track: bool
    album_playlist_key: str | None

    # TODO: Validate
    def __init__(self, files: YouTubeShared) -> None:
        self._files = files

    # TODO: Validate
    def parse(self, url: str) -> None:  # noqa: PLR0911 - One return per kind of address.
        self.video_key = None
        self.whole_title = False
        self.musician_track = False
        self.album_playlist_key = None

        if match := re.match(PLAYLIST_VIDEO_URL_REGEX, url):
            self.video_key = match.group("video_key")
            self._parse_playlist(match.group("playlist_key"), url)
            return

        if match := re.match(TITLE_PLAYLIST_URL_REGEX, url):
            self._parse_title_playlist(match.group("title_playlist_key"), url)
            return

        if match := re.match(PLAYLIST_URL_REGEX, url):
            self._parse_playlist(match.group("playlist_key"), url)
            return

        if match := re.match(VIDEO_URL_REGEX, url):
            self._parse_video(match.group("video_key"), url)
            return

        if match := re.match(CHANNEL_KEY_URL_REGEX, url):
            channel_key = match.group("channel_key")
            self._parsed_channel(
                self._files.channel_by_channel_id_file(channel_key),
                url,
            )
            self._parse_channel(channel_key, url)
            return

        if match := re.match(TITLE_URL_REGEX, url):
            self._parse_title(match.group("title_key"), url)
            return

        if match := re.match(CHANNEL_USERNAME_URL_REGEX, url):
            parsed = self._parsed_channel(
                self._files.channel_by_username_file(match.group("channel_username")),
                url,
            )
            self._parse_channel(get_first_item(parsed.items).id, url)
            return

        if match := re.match(CHANNEL_HANDLE_URL_REGEX, url):
            parsed = self._parsed_channel(
                self._files.channel_by_handle_file(match.group("channel_handle")),
                url,
            )
            self._parse_channel(get_first_item(parsed.items).id, url)
            return

        msg = f"Invalid {self._files.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _parsed_channel(self, channel_file: BaseFile[Any], url: str) -> ChannelsModel:
        self._files.raise_if_invalid_file(channel_file, url)
        channel: ChannelsModel = channel_file.parsed()
        if not channel.items:
            msg = f"Invalid {self._files.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        return channel

    # TODO: Validate
    def _raise_if_invalid_channel(self, channel_key: str, url: str) -> None:
        self._parsed_channel(self._files.channel_by_channel_id_file(channel_key), url)

    # TODO: Validate
    def _parse_playlist(self, playlist_key: str, url: str) -> None:
        self.playlist_key = playlist_key

        if is_channel_uploads_playlist_key(playlist_key):
            self.title_key = channel_key_from_uploads_playlist_key(playlist_key)
            self._raise_if_invalid_channel(self.title_key, url)
            return

        if is_an_album(playlist_key):
            music_playlist_file = self._files.music_playlist_file(playlist_key)
            self._files.raise_if_invalid_file(music_playlist_file, url)
            channel_key = music_playlist_file.artist_channel_id()
            if not channel_key:
                self.title_key = playlist_key
                return
            self._raise_if_invalid_channel(channel_key, url)
            self.album_playlist_key = playlist_key
            self.title_key = channel_key
            return

        playlist_items_file = self._files.playlist_items_file(playlist_key)
        self._files.raise_if_invalid_file(playlist_items_file, url)
        self.title_key = get_first_item(
            playlist_items_file.parsed().items,
        ).snippet.channel_id

    # TODO: Validate
    def _parse_video(self, video_key: str, url: str) -> None:
        self.video_key = video_key
        videos_file = self._files.videos_file(video_key)
        self._files.raise_if_invalid_file(videos_file, url)

        channel_key = videos_file.parsed().items[0].snippet.channel_id
        if is_free_movies_channel(channel_key):
            self.title_key = video_key
        else:
            self.title_key = channel_key

        if is_video_key(self.title_key):
            self.playlist_key = self.title_key
            return

        self._raise_if_invalid_channel(self.title_key, url)

        if is_topic_channel(self._files.channel_by_channel_id_file(self.title_key)):
            self.playlist_key = self.title_key
            self.musician_track = True
        else:
            self.playlist_key = channel_uploads_playlist_key(self.title_key)

    # TODO: Validate
    def _parse_title_playlist(self, title_playlist_key: str, url: str) -> None:
        title_listing_file = self._files.browse_file(title_playlist_key)
        self._files.raise_if_invalid_file(title_listing_file, url)
        title_key = title_listing_file.title_key()
        if title_key is None:
            msg = f"Invalid {self._files.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        self.title_key = title_key
        self.playlist_key = title_key
        self.whole_title = True

    # TODO: Validate
    def _parse_title(self, title_key: str, url: str) -> None:
        self.title_key = title_key
        self._files.raise_if_invalid_file(self._files.browse_file(title_key), url)
        if not title_season_numbers_from_file(self._files.browse_file(title_key)):
            msg = f"Invalid {self._files.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        season = parse_qs(urlparse(url).query).get("season", [])
        if season:
            self.playlist_key = title_season_key(title_key, season[0])
        else:
            self.playlist_key = title_key
            self.whole_title = True

    # TODO: Validate
    def _parse_channel(self, title_key: str, url: str) -> None:
        self.title_key = title_key
        self._raise_if_invalid_channel(title_key, url)

        if is_free_movies_channel(title_key):
            msg = (
                f"{title_key} does not list most of the videos it owns, so import "
                f"the URL of an individual video instead of the channel: {url}"
            )
            raise InvalidURLError(msg)

        if is_topic_channel(self._files.channel_by_channel_id_file(title_key)):
            self.playlist_key = title_key
            self.whole_title = True
        else:
            self.playlist_key = channel_uploads_playlist_key(title_key)
