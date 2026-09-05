# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, override
from urllib.parse import parse_qs, urlparse

from app.shows.models import Show
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin_v2.importer import BaseImporter
from plugins.YouTube.base import YouTubeBase
from plugins.YouTube.constants import LONG_DOMAIN_REGEX, SHORT_DOMAIN_REGEX
from plugins.YouTube.files import (
    get_first_item,
    is_an_album,
    is_channel_uploads_playlist_key,
    is_video_key,
    show_season_key,
)
from plugins.YouTube.utils import (
    channel_key_from_uploads_playlist_key,
    is_free_movies_channel,
)

if TYPE_CHECKING:
    from not_yt_dlapi.channels.models import ChannelsModel

    from plugins.utils.base_plugin_v2.files import BaseFile


# TODO: Validate
class YouTubeImporter(BaseImporter, YouTubeBase):
    _show_key: str

    # https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    # https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    _PLAYLIST_VIDEO_URL_REGEX = (
        rf"(?:{LONG_DOMAIN_REGEX}|{SHORT_DOMAIN_REGEX})"
        r"\/(?:watch\?v=)?(?P<video_key>[A-Za-z0-9_-]{11})[?&]"
        r"list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
    )
    # https://www.youtube.com/playlist?list=TVSHX2-tv9KBHSAWLsDbH3h9vNzwxEAyyqXMw
    _SHOW_PLAYLIST_URL_REGEX = (
        LONG_DOMAIN_REGEX + r"\/playlist\?list=(?P<show_playlist_key>TVSH[^&]+)"
    )
    # https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
    _PLAYLIST_URL_REGEX = (
        LONG_DOMAIN_REGEX
        + r"\/playlist\?list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
    )
    # https://www.youtube.com/watch?v=jNQXAC9IVRw
    # https://www.youtube.com/shorts/jNQXAC9IVRw
    # https://youtu.be/jNQXAC9IVRw
    _VIDEO_URL_REGEX = (
        rf"(?:{LONG_DOMAIN_REGEX}\/(?:watch\?v=|shorts\/)|{SHORT_DOMAIN_REGEX}\/)"
        r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&])"
    )
    # https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A
    _CHANNEL_KEY_URL_REGEX = (
        LONG_DOMAIN_REGEX + r"\/channel\/(?P<channel_key>UC.{22})(?:$|\/)"
    )
    # https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw
    # https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw?season=23&sbp=...
    _SHOW_URL_REGEX = (
        LONG_DOMAIN_REGEX + r"\/show\/(?P<show_key>SC[A-Za-z0-9_-]+?)(?:$|[/?])"
    )
    # https://www.youtube.com/user/jawed
    _CHANNEL_USERNAME_URL_REGEX = (
        LONG_DOMAIN_REGEX + r"\/user\/(?P<channel_username>.+?)(?:$|\/)"
    )
    # https://www.youtube.com/@jawed
    # https://www.youtube.com/c/jawed
    # https://www.youtube.com/jawed
    _CHANNEL_HANDLE_URL_REGEX = (
        LONG_DOMAIN_REGEX + r"\/(?:c\/|@)?(?P<channel_handle>.+?)(?:$|\/)"
    )

    _playlist_key: str
    _video_key: str | None
    _whole_show: bool
    _musician_track: bool

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            cls._PLAYLIST_VIDEO_URL_REGEX,  # Must be first due to regex overlap
            cls._SHOW_PLAYLIST_URL_REGEX,
            cls._PLAYLIST_URL_REGEX,
            cls._VIDEO_URL_REGEX,
            cls._CHANNEL_KEY_URL_REGEX,
            cls._SHOW_URL_REGEX,
            cls._CHANNEL_USERNAME_URL_REGEX,
            cls._CHANNEL_HANDLE_URL_REGEX,
        )

    # Every address carries the domain it is written under, because a video is
    # named on the long domain and the short one alike, so the domain is not put
    # in front of them here the way it is for every other plugin.
    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        alternatives = "|".join(
            # Strip named groups to non-capturing so addresses that share a group name
            # (e.g. playlist_key) do not collide when the alternatives are combined.
            re.sub(r"\(\?P<[^>]+>", "(?:", url_regex)
            for url_regex in cls._url_regexes()
        )
        return f"(?:{alternatives})"

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:  # noqa: PLR0911 - One return per kind of address.
        self._video_key = None
        self._whole_show = False
        self._musician_track = False

        if match := re.match(self._PLAYLIST_VIDEO_URL_REGEX, url):
            self._video_key = match.group("video_key")
            self._read_playlist(match.group("playlist_key"), url)
            return self._show_key

        if match := re.match(self._SHOW_PLAYLIST_URL_REGEX, url):
            self._read_show_playlist(match.group("show_playlist_key"), url)
            return self._show_key

        if match := re.match(self._PLAYLIST_URL_REGEX, url):
            self._read_playlist(match.group("playlist_key"), url)
            return self._show_key

        if match := re.match(self._VIDEO_URL_REGEX, url):
            self._read_video(match.group("video_key"), url)
            return self._show_key

        if match := re.match(self._CHANNEL_KEY_URL_REGEX, url):
            channel_key = match.group("channel_key")
            self._parsed_channel(self.channel_by_channel_id_file(channel_key), url)
            self._read_channel(channel_key, url)
            return self._show_key

        if match := re.match(self._SHOW_URL_REGEX, url):
            self._read_show(match.group("show_key"), url)
            return self._show_key

        if match := re.match(self._CHANNEL_USERNAME_URL_REGEX, url):
            parsed = self._parsed_channel(
                self.channel_by_username_file(match.group("channel_username")),
                url,
            )
            self._read_channel(get_first_item(parsed.items).id, url)
            return self._show_key

        if match := re.match(self._CHANNEL_HANDLE_URL_REGEX, url):
            parsed = self._parsed_channel(
                self.channel_by_handle_file(match.group("channel_handle")),
                url,
            )
            self._read_channel(get_first_item(parsed.items).id, url)
            return self._show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _parsed_channel(self, channel_file: BaseFile[Any], url: str) -> ChannelsModel:
        self.raise_if_invalid_file(channel_file, url)
        channel: ChannelsModel = channel_file.parsed()
        # The API answers a channel it has nothing under with an empty listing
        # rather than by refusing, so a URL naming no channel is only known from
        # what came back holding none.
        if not channel.items:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        return channel

    # TODO: Validate
    def _raise_if_invalid_channel(self, channel_key: str, url: str) -> None:
        self._parsed_channel(self.channel_by_channel_id_file(channel_key), url)

    # TODO: Validate
    def _read_playlist(self, playlist_key: str, url: str) -> None:
        self._playlist_key = playlist_key

        # A channel's uploads are a season of that channel rather than a listing of
        # their own, and the playlist they are listed as is named after the channel,
        # so the channel is read off the key rather than looked up.
        if is_channel_uploads_playlist_key(playlist_key):
            self._show_key = channel_key_from_uploads_playlist_key(playlist_key)
            self._raise_if_invalid_channel(self._show_key, url)
            return

        # A release belongs to the musician's Topic channel, which is the show its
        # tracks went up on, so importing it brings in the musician rather than the
        # release on its own. A release whose tracks went up somewhere else is its
        # own show, since a channel that is not a Topic lists far more than music.
        if is_an_album(playlist_key):
            music_playlist_file = self.music_playlist_file(playlist_key)
            self.raise_if_invalid_file(music_playlist_file, url)
            channel_key = music_playlist_file.artist_channel_id()
            if not channel_key:
                self._show_key = playlist_key
                return
            # The release is imported as one of the musician's when the channel its
            # tracks went up on is a Topic channel, which is something only that
            # channel says.
            self._raise_if_invalid_channel(channel_key, url)
            # Nothing the channel lists names the release, so what the URL named is
            # remembered for the seasons of the channel to be read with.
            self.record_album_playlist_key(playlist_key)
            self._show_key = channel_key
            return

        playlist_items_file = self.playlist_items_file(playlist_key)
        self.raise_if_invalid_file(playlist_items_file, url)
        self._show_key = get_first_item(
            playlist_items_file.parsed().items,
        ).snippet.channel_id

    # TODO: Validate
    def _read_video(self, video_key: str, url: str) -> None:
        self._video_key = video_key
        videos_file = self.videos_file(video_key)
        self.raise_if_invalid_file(videos_file, url)

        channel_key = videos_file.parsed().items[0].snippet.channel_id
        # A channel that never lists this video cannot be imported to reach it, so the
        # video is imported as a show of its own instead.
        if is_free_movies_channel(channel_key):
            self._show_key = video_key
        else:
            self._show_key = channel_key

        if is_video_key(self._show_key):
            self._playlist_key = self._show_key
            return

        # Whether the show the video belongs to is a musician rather than a channel
        # is something only the channel says, and what the URL brought in is named
        # by seasons that differ between the two.
        self._raise_if_invalid_channel(self._show_key, url)

        # A track on a Topic channel is listed by the release it is on rather than
        # by an uploads season, and which release that is only the musician's own
        # listing says, so the URL asks for the musician.
        if self.is_topic_channel(self._show_key):
            self._playlist_key = self._show_key
            self._musician_track = True
        else:
            self._playlist_key = self.channel_uploads_playlist_key(self._show_key)

    # TODO: Validate
    def _read_show_playlist(self, show_playlist_key: str, url: str) -> None:
        show_listing_file = self.show_listing_file(show_playlist_key)
        self.raise_if_invalid_file(show_listing_file, url)
        show_key = show_listing_file.show_key()
        if show_key is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        self._show_key = show_key
        self._playlist_key = show_key
        self._whole_show = True
        self.raise_if_invalid_file(self.show_page_file(show_key), url)

    # TODO: Validate
    def _read_show(self, show_key: str, url: str) -> None:
        self._show_key = show_key
        # The page names the playlist the listing is asked for by, so it is read
        # before the listing rather than beside it.
        self.raise_if_invalid_file(self.show_page_file(show_key), url)
        self.raise_if_invalid_file(self.show_listing_file_for_show(show_key), url)
        if not self.show_season_numbers_from_file(show_key):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        # A URL for one season only asks for that season, where a URL for the show
        # asks for all of it.
        season = parse_qs(urlparse(url).query).get("season", [])
        if season:
            self._playlist_key = show_season_key(show_key, season[0])
        else:
            self._playlist_key = show_key
            self._whole_show = True

    # TODO: Validate
    def _read_channel(self, show_key: str, url: str) -> None:
        self._show_key = show_key
        # A handle and a username are looked up in files of their own, and the
        # channel the key names is what says whether it is a Topic channel, so it is
        # read here rather than left to whatever asks first.
        self._raise_if_invalid_channel(show_key, url)

        # The channel only lists a fraction of the videos it owns, so importing it
        # would import almost none of them. Its videos are imported one at a time.
        if is_free_movies_channel(show_key):
            msg = (
                f"{show_key} does not list most of the videos it owns, so import "
                f"the URL of an individual video instead of the channel: {url}"
            )
            raise InvalidURLError(msg)

        # A Topic channel has no uploads season, because what it lists is releases,
        # so the URL asks for the channel itself the way a show URL does.
        if self.is_topic_channel(show_key):
            self._playlist_key = show_key
            self._whole_show = True
        else:
            self._playlist_key = self.channel_uploads_playlist_key(show_key)

    # A YouTube show is always imported for a specific playlist.
    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        show_key = self._url_to_show_key(url)
        show_preload = self._preload_show(show_key, preload_episodes=True)
        existing_show = show_preload.one_or_none()

        if not existing_show:
            _cache = self._download_show_files_and_children(show_key)
            existing_show = self.upsert_show(self.source, show_key)

        # If a channel is imported but a new playlist is added and that playlist is the
        # URL being imported this will update the channel information to include that
        # playlist.
        elif self._playlist_is_missing(existing_show, self._playlist_key):
            self._download_outdated_files(
                self._show_files(show_key),
                tz_datetime.now(),
            )
            existing_show = self.upsert_show(self.source, show_key)

        return self._import_results(existing_show)

    # TODO: Validate
    @override
    def _import_results(self, show: Show) -> list[URLImportResult]:
        if self._whole_show:
            return [URLImportResult.show_import_results(show)]

        if self._video_key is None:
            seasons = [
                season for season in show.seasons if season.key == self._playlist_key
            ]
            return [URLImportResult.season_import_results(show, seasons)]

        # The track is looked for in every release of the musician, since the URL
        # named no release and the show holds one season for each of them.
        if self._musician_track:
            return [
                URLImportResult.episode_import_results(
                    show,
                    [
                        episode
                        for season in show.seasons
                        for episode in season.episodes
                        if episode.key == self._video_key
                    ],
                ),
            ]

        return [
            URLImportResult.episode_import_results(
                show,
                [
                    episode
                    for season in show.seasons
                    if season.key == self._playlist_key
                    for episode in season.episodes
                    if episode.key == self._video_key
                ],
            ),
        ]
