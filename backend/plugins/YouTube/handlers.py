# TODO: Validate
from __future__ import annotations

import re
from abc import abstractmethod
from typing import TYPE_CHECKING, override
from urllib.parse import parse_qs, urlparse

from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.url import URLHandler, URLMixin
from plugins.YouTube.files import (
    channel_key_from_uploads_playlist_key,
    get_first_item,
    is_channel_uploads_playlist_key,
    is_free_movies_channel,
    is_music_playlist_key,
    is_video_key,
    show_season_key,
    system_hub_channel_name,
)

if TYPE_CHECKING:
    from not_yt_dlapi.channels.models import ChannelListResponse

    from app.shows.models import Show
    from plugins.YouTube import YouTube
    from plugins.YouTube.files import (
        ChannelByChannelId,
        ChannelByHandle,
        ChannelByUsername,
        YouTubeJSON,
    )


LONG_DOMAIN = "youtube.com"
SHORT_DOMAIN = "youtu.be"
_LONG_DOMAIN_REGEX = URLMixin._regex_escape_domain(LONG_DOMAIN)  # noqa: SLF001 - Same package.
_SHORT_DOMAIN_REGEX = URLMixin._regex_escape_domain(SHORT_DOMAIN)  # noqa: SLF001 - Same package.


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
    @override
    def url_regex(cls, domain_regex: str) -> str:
        return _LONG_DOMAIN_REGEX + cls._URL_REGEX

    # TODO: Validate
    @property
    @abstractmethod
    def playlist_key(self) -> str: ...

    # TODO: Validate
    @property
    def video_key(self) -> str | None:
        return None

    # TODO: Validate
    def _raise_if_invalid_channel(self, channel_key: str) -> None:
        channel_file = self.plugin.channel_by_channel_id_file(channel_key)
        self.plugin.raise_if_invalid_file(channel_file, self.url)
        # The API answers a channel it has nothing under with an empty listing
        # rather than by refusing, so a URL naming no channel is only known from
        # what came back holding none.
        if not channel_file.parsed().items:
            msg = f"Invalid {self.plugin.plugin_key()} URL: {self.url}"
            raise InvalidURLError(msg)

    # TODO: Validate
    def _raise_if_system_hub_channel(self, channel_key: str) -> None:
        hub_name = system_hub_channel_name(channel_key)
        if hub_name is not None:
            msg = (
                f"{channel_key} is YouTube's system generated {hub_name} hub, which "
                f"owns no videos of its own and cannot be imported: {self.url}"
            )
            raise InvalidURLError(msg)


# TODO: Validate
class VideoURLHandler(YouTubeURLHandler):
    # https://www.youtube.com/watch?v=jNQXAC9IVRw
    # https://www.youtube.com/shorts/jNQXAC9IVRw
    # https://youtu.be/jNQXAC9IVRw
    _URL_REGEX = r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&])"

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls, domain_regex: str) -> str:
        long_paths = rf"{_LONG_DOMAIN_REGEX}\/(?:watch\?v=|shorts\/)"
        short_path = rf"{_SHORT_DOMAIN_REGEX}\/"
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
        if is_free_movies_channel(channel_key):
            return self.video_key
        return channel_key

    # TODO: Validate
    @property
    def playlist_key(self) -> str:
        show_key = self.show_key
        if is_video_key(show_key):
            return show_key
        # A track on a Topic channel is listed by the release it is on rather than
        # by an uploads season, and which release that is only the musician's own
        # listing says, so the URL asks for the musician.
        if self.plugin.is_topic_channel(show_key):
            return show_key
        return self.plugin.channel_uploads_playlist_key(show_key)

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.videos_file(self.video_key),
            self.url,
        )
        # Whether the show the video belongs to is a musician rather than a channel
        # is something only the channel says, and what the URL brought in is named
        # by seasons that differ between the two.
        show_key = self.show_key
        if not is_video_key(show_key):
            self._raise_if_invalid_channel(show_key)

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        # The track is looked for in every release of the musician, since the URL
        # named no release and the show holds one season for each of them.
        if self.playlist_key == show.key and not is_video_key(show.key):
            return [
                URLImportResult.for_episodes(
                    show,
                    [
                        episode
                        for season in show.seasons
                        for episode in season.episodes
                        if episode.key == self.video_key
                    ],
                ),
            ]
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
        # A channel's uploads are a season of that channel rather than a listing of
        # their own, and the playlist they are listed as is named after the channel,
        # so the channel is read off the key rather than looked up.
        if is_channel_uploads_playlist_key(self.playlist_key):
            return channel_key_from_uploads_playlist_key(self.playlist_key)
        # A release belongs to the musician's Topic channel, which is the show its
        # tracks went up on, so importing it brings in the musician rather than the
        # release on its own. A release whose tracks went up somewhere else is its
        # own show, since a channel that is not a Topic lists far more than music.
        if is_music_playlist_key(self.playlist_key):
            channel_key = (
                self.plugin.music_playlist_file(self.playlist_key)
                .parsed()
                .artist_channel_id
            )
            if not channel_key:
                return self.playlist_key
            # Nothing the channel lists names the release, so what the URL named is
            # remembered for the seasons of the channel to be read with.
            self.plugin.record_album_playlist_key(self.playlist_key)
            return channel_key
        playlist_items_file = self.plugin.playlist_items_file(self.playlist_key)
        return get_first_item(playlist_items_file.parsed().items).snippet.channel_id

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        if is_channel_uploads_playlist_key(self.playlist_key):
            self._raise_if_invalid_channel(self.show_key)
            self._raise_if_system_hub_channel(self.show_key)
            return

        if is_music_playlist_key(self.playlist_key):
            music_playlist_file = self.plugin.music_playlist_file(self.playlist_key)
            self.plugin.raise_if_invalid_file(music_playlist_file, self.url)
            # The release is imported as one of the musician's when the channel its
            # tracks went up on is a Topic channel, which is something only that
            # channel says.
            channel_key = music_playlist_file.parsed().artist_channel_id
            if channel_key:
                self._raise_if_invalid_channel(channel_key)
            return

        playlist_items_file = self.plugin.playlist_items_file(self.playlist_key)
        self.plugin.raise_if_invalid_file(playlist_items_file, self.url)
        first_item = get_first_item(playlist_items_file.parsed().items)
        self._raise_if_system_hub_channel(first_item.snippet.channel_id)


# TODO: Validate
class PlaylistURLHandler(PlaylistBasedURLHandler):
    # https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    _URL_REGEX = r"\/playlist\?list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"

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
        r"list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
    )

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls, domain_regex: str) -> str:
        return rf"(?:{_LONG_DOMAIN_REGEX}|{_SHORT_DOMAIN_REGEX})" + cls._URL_REGEX

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
class ShowPlaylistURLHandler(YouTubeURLHandler):
    # https://www.youtube.com/playlist?list=TVSHX2-tv9KBHSAWLsDbH3h9vNzwxEAyyqXMw
    _URL_REGEX = r"\/playlist\?list=(?P<show_playlist_key>TVSH[^&]+)"

    # TODO: Validate
    @property
    def _show_playlist_key(self) -> str:
        return self._match.group("show_playlist_key")

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        show_key = self.plugin.show_listing_file(self._show_playlist_key).show_key()
        if show_key is None:
            msg = f"Invalid {self.plugin.plugin_key()} URL: {self.url}"
            raise InvalidURLError(msg)
        return show_key

    # TODO: Validate
    @property
    @override
    def playlist_key(self) -> str:
        return self.show_key

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.show_listing_file(self._show_playlist_key),
            self.url,
        )
        self.plugin.raise_if_invalid_file(
            self.plugin.show_page_file(self.show_key),
            self.url,
        )

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        return [URLImportResult.for_show(show)]


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
        # The page names the playlist the listing is asked for by, so it is read
        # before the listing rather than beside it.
        self.plugin.raise_if_invalid_file(
            self.plugin.show_page_file(self.show_key),
            self.url,
        )
        self.plugin.raise_if_invalid_file(
            self.plugin.show_listing_file_for_show(self.show_key),
            self.url,
        )
        if not self.plugin.show_season_numbers(self.show_key):
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
    def _channel_file(self) -> YouTubeJSON[ChannelListResponse]:
        """Return the file that resolves the URL to a channel."""

    # TODO: Validate
    @property
    @override
    def playlist_key(self) -> str:
        # A Topic channel has no uploads season, because what it lists is releases,
        # so the URL asks for the channel itself the way a show URL does.
        if self.plugin.is_topic_channel(self.show_key):
            return self.show_key
        return self.plugin.channel_uploads_playlist_key(self.show_key)

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(self._channel_file, self.url)
        if not self._channel_file.parsed().items:
            msg = f"Invalid {self.plugin.plugin_key()} URL: {self.url}"
            raise InvalidURLError(msg)
        # A handle and a username are looked up in files of their own, and the
        # channel the key names is what says whether it is a Topic channel, so it is
        # read here rather than left to whatever asks first.
        self._raise_if_invalid_channel(self.show_key)
        self._raise_if_system_hub_channel(self.show_key)

        # The channel only lists a fraction of the videos it owns, so importing it
        # would import almost none of them. Its videos are imported one at a time.
        if is_free_movies_channel(self.show_key):
            msg = (
                f"{self.show_key} does not list most of the videos it owns, so import "
                f"the URL of an individual video instead of the channel: {self.url}"
            )
            raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def import_results(self, show: Show) -> list[URLImportResult]:
        return [URLImportResult.for_show(show)]


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
    @override
    def raise_if_invalid(self) -> None:
        self._raise_if_system_hub_channel(self.show_key)
        super().raise_if_invalid()

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
