# TODO: Validate
import json
import re
import time
from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import cache
from typing import Any, get_args, override

from loguru import logger
from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.channels.models import ChannelListResponse
from not_yt_dlapi.exceptions import APIError, HTTPError, NotFoundError
from not_yt_dlapi.feed_models import FeedResponse
from not_yt_dlapi.music.models import MusicPlaylist
from not_yt_dlapi.playlist_items.models import PlaylistItemListResponse
from not_yt_dlapi.playlists.models import PlaylistListResponse
from not_yt_dlapi.shows.models import Show as ShowListingResponse
from not_yt_dlapi.shows.models import ShowEpisode
from not_yt_dlapi.topic.models import TopicRelease, TopicReleases
from not_yt_dlapi.videos.models import VideoListResponse
from sqlmodel import Session

from app.config import settings
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    BaseFile,
    HTMLFile,
    JSONFile,
    ResponseJSON,
    ResponseModel,
    XMLFile,
)
from plugins.utils.get_around_client import get_around_client


@cache
def not_yt_dlapi() -> NotYTDLAPI:
    return NotYTDLAPI(
        api_key=settings.YOUTUBE_API_KEY,
        get_around_client=get_around_client(),
    )


# TODO: Validate
class YouTubeJSON[T: ResponseModel](ResponseJSON[T]):
    # TODO: Validate
    @override
    def parsed(self) -> T:
        if self._cached_parsed is None:
            if not (content := self.database_record.content):
                msg = "File content is empty, cannot parse."
                raise ValueError(msg)
            model: Any = get_args(type(self).__orig_bases__[0])[0]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            parsed: T = model.from_response(content)
            self._cached_parsed = parsed
        return self._cached_parsed


# TODO: Validate
def is_music_playlist_key(key: str) -> bool:
    """Report whether a playlist key belongs to an auto-generated album."""
    return key.startswith("OLAK5uy_")


# TODO: Validate
def is_channel_key(key: str) -> bool:
    """Report whether a key belongs to a channel rather than to what one holds."""
    return not (is_video_key(key) or is_show_key(key) or is_music_playlist_key(key))


# The official YouTube Movies & TV channel. Its uploads playlist and playlist listing
# are truncated, so most of the videos it owns are missing from every listing the
# channel exposes and can only be reached by importing them one at a time.
_FREE_MOVIES_CHANNEL_KEY = "UCuVPpxrm2VAgpH3Ktln4HXg"


# TODO: Validate
def is_free_movies_channel(channel_key: str) -> bool:
    """Report whether a channel is the one YouTube's free catalogue is published on.

    Everything YouTube serves free with ads is owned by this one channel, and a
    title that has to be bought or rented is owned by a channel generated for
    that title alone, so who owns a video is what says which of the two it is.
    """
    return channel_key == _FREE_MOVIES_CHANNEL_KEY


_SYSTEM_HUB_CHANNELS = {
    "XXX___UC-9-kyTW8ZkZNDHQJ6FgpwQ": "Music",
    "XXX___UClgRkhTL3_hImCAmdLfDE4g": "Movies & Shows",
    "XXX___UCOpNcN46UbXVtpKMrmU4Abg": "Gaming",
    "XXX___UCEgdi0XIXXZ-qJOFPf4JSKw": "Sports",
    "XXX___UCYfdidRxbB8Qhf0Nx7ioOYw": "News",
    "XXX___UC4R8DWoMoI7CAwX8_LjQHig": "Live",
    "XXX___UCrpQ4p1Ql_hG8rKXIKM1MOQ": "Fashion & Beauty",
    "XXX___UCtFRv9O2AHqOZjjynzrv-xg": "Learning",
    "XXX___UCzuqhhs6NWbgTzMuM09WKDQ": "360 / Virtual Reality",
}


# TODO: Validate
def system_hub_channel_name(channel_key: str) -> str | None:
    return _SYSTEM_HUB_CHANNELS.get(channel_key)


# TODO: Validate
def is_video_key(key: str) -> bool:
    """Report whether a key belongs to a video rather than a channel or playlist.

    A standalone video is its own show, season and episode, all keyed by the video,
    and every channel and playlist key is longer than a video key.
    """
    # Videos are always 11 characters long and channels/playlists are never 11
    # characters long.
    return len(key) == 11  # noqa: PLR2004


# TODO: Validate
def is_show_key(key: str) -> bool:
    """Report whether a key belongs to a show page."""
    return key.startswith("SC")


# TODO: Validate
def is_channel_uploads_playlist_key(key: str) -> bool:
    return key.startswith("UU")


# TODO: Validate
def channel_key_from_uploads_playlist_key(key: str) -> str:
    return key[:1] + "C" + key[2:]


# TODO: Validate
def show_season_key(show_key: str, season_number: str) -> str:
    """Return the season key for one season of a show."""
    return f"{show_key}/{season_number}"


# TODO: Validate
def is_show_season_key(key: str) -> bool:
    """Report whether a key belongs to one season of a show."""
    return is_show_key(key) and "/" in key


# TODO: Validate
def split_show_season_key(season_key: str) -> tuple[str, str]:
    """Split a season key back into its show key and season number."""
    show_key, _, season_number = season_key.partition("/")
    return show_key, season_number


# TODO: Validate
def is_quota_error(error: BaseException) -> bool:
    """Report whether `error` is the YouTube API refusing calls until quota resets."""
    if not isinstance(error, APIError):
        return False
    errors = error.response.get("error", {}).get("errors", [])
    return any(
        item.get("reason") in frozenset({"dailyLimitExceeded", "quotaExceeded"})
        for item in errors
    )


# TODO: Validate
def get_first_item[T](items: Sequence[T] | None) -> T:
    if not items:
        msg = "Expected at least one item, got none"
        raise ValueError(msg)
    return items[0]


# TODO: Validate
def _merge_pages(pages: list[str]) -> dict[str, Any]:
    """Merge paginated API responses into a single response with all items."""
    parsed_pages = [json.loads(page) for page in pages]
    merged = dict(parsed_pages[0])
    merged["items"] = [item for page in parsed_pages for item in page.get("items", [])]
    return merged


class ChannelByChannelId(YouTubeJSON[ChannelListResponse]):
    API_ENDPOINT = not_yt_dlapi().channels

    @override
    def _fetch(self) -> ChannelListResponse:
        return self.API_ENDPOINT.list(channel_id=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, NotFoundError)


class ChannelByHandle(YouTubeJSON[ChannelListResponse]):
    API_ENDPOINT = not_yt_dlapi().channels

    @override
    def _fetch(self) -> ChannelListResponse:
        return self.API_ENDPOINT.list(channel_handle=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, NotFoundError)


# TODO: Validate
class ChannelByUsername(YouTubeJSON[ChannelListResponse]):
    API_ENDPOINT = not_yt_dlapi().channels

    @override
    def _fetch(self) -> ChannelListResponse:
        return self.API_ENDPOINT.list(channel_username=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, NotFoundError)


# TODO: Validate
class ChannelPlaylists(YouTubeJSON[PlaylistListResponse]):
    API_ENDPOINT = not_yt_dlapi().playlists

    # TODO: Validate
    @override
    def _fetch(self) -> PlaylistListResponse:
        pages: list[str] = []
        page_token: str | None = None
        while True:
            page = self.API_ENDPOINT.list(
                channel_id=self.unique_identifier,
                page_token=page_token,
            )
            pages.append(page.raw)
            page_token = page.next_page_token
            if page_token is None:
                break
        return PlaylistListResponse.from_response(json.dumps(_merge_pages(pages)))

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, NotFoundError)


class PlaylistInfo(YouTubeJSON[PlaylistListResponse]):
    API_ENDPOINT = not_yt_dlapi().playlists

    @override
    def _fetch(self) -> PlaylistListResponse:
        return self.API_ENDPOINT.list(playlist_ids=self.unique_identifier)


# TODO: Validate
class PlaylistItems(YouTubeJSON[PlaylistItemListResponse]):
    """Playlist items file."""

    API_ENDPOINT = not_yt_dlapi().playlist_items

    # TODO: Validate
    def _all_pages(self) -> list[str]:
        pages: list[str] = []
        page_token: str | None = None
        while True:
            page = self.API_ENDPOINT.list(
                self.unique_identifier,
                page_token=page_token,
            )
            pages.append(page.raw)
            page_token = page.next_page_token
            if page_token is None:
                return pages

    # Due to API limits this function merges new videos with existing videos instead of
    # downloading all videos every time which over time will lead to a messy file with
    # dead videos.
    # TODO: Validate
    @override
    def _fetch(self) -> PlaylistItemListResponse:
        # If this is the first time downloading the file download everything.
        if not self._existing_database_record:
            return PlaylistItemListResponse.from_response(
                json.dumps(_merge_pages(self._all_pages())),
            )

        # If the entry is over a year old download a fresh non-canonical row to clean
        # out deleted videos. Album playlists are auto-generated and never change, so
        # re-paging them would spend quota to rediscover the same tracks.
        year_ago_datetime = tz_datetime.now() - timedelta(days=365)
        if (
            not is_music_playlist_key(self.unique_identifier)
            and self._existing_database_record.data_timestamp < year_ago_datetime
        ):
            return PlaylistItemListResponse.from_response(
                json.dumps(_merge_pages(self._all_pages())),
            )

        existing_items: list[dict[str, Any]] = json.loads(
            self.database_record.content or "{}",
        )["items"]
        existing_video_ids = {
            item["contentDetails"]["videoId"] for item in existing_items
        }

        pages: list[str] = []
        page_token: str | None = None
        reached_existing_video = False
        while not reached_existing_video:
            page = self.API_ENDPOINT.list(
                self.unique_identifier,
                page_token=page_token,
            )
            pages.append(page.raw)
            # Everything from the first already stored video onwards is already stored,
            # so the remaining pages do not need to be spent on.
            reached_existing_video = any(
                item.content_details.video_id in existing_video_ids
                for item in page.items
            )
            page_token = page.next_page_token
            if not page_token:
                break

        merged = _merge_pages(pages)
        # Paging to the end of the playlist without reaching a stored video means the
        # download covers the whole playlist, so keeping the stored items would keep
        # videos that have since been removed.
        if not reached_existing_video:
            return PlaylistItemListResponse.from_response(json.dumps(merged))

        new_ids = {item["contentDetails"]["videoId"] for item in merged["items"]}
        merged["items"] = merged["items"] + [
            item
            for item in existing_items
            if item["contentDetails"]["videoId"] not in new_ids
        ]
        return PlaylistItemListResponse.from_response(json.dumps(merged))

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, NotFoundError)


# TODO: Validate
class Videos(YouTubeJSON[VideoListResponse]):
    """Videos file."""

    API_ENDPOINT = not_yt_dlapi().videos

    # TODO: Validate
    @override
    def _fetch(self) -> VideoListResponse:
        return self.API_ENDPOINT.list(self.unique_identifier)


# TODO: Validate
class MusicPlaylistFile(YouTubeJSON[MusicPlaylist]):
    API_ENDPOINT = not_yt_dlapi().music

    # TODO: Validate
    @override
    def _fetch(self) -> MusicPlaylist:
        return self.API_ENDPOINT.list(self.unique_identifier)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, NotFoundError)


# TODO: Validate
class TopicReleasesFile(JSONFile[TopicReleases]):
    """The albums and singles a musician's Topic channel lists.

    The channel lists a dozen releases on a shelf and the rest behind it, and a
    shelf release is listed again by the first page behind it, so the pages are
    stored as they were served and read back as one listing with each release
    named once.
    """

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                pages = not_yt_dlapi().topic.list_all(self.unique_identifier)
            except NotFoundError:
                self.write(None, f"Invalid unique_identifier {self.unique_identifier}")
            else:
                self.write([json.loads(page.raw) for page in pages])

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> TopicReleases:
        pages = [TopicReleases.from_response(json.dumps(page)) for page in raw]
        seen: set[str] = set()
        releases: list[TopicRelease] = []
        for page in pages:
            for release in page.releases:
                if release.playlist_id not in seen:
                    seen.add(release.playlist_id)
                    releases.append(release)
        return pages[0].model_copy(update={"releases": releases})


# TODO: Validate
class ShowListing(JSONFile[list[ShowListingResponse]]):
    """Every season of a show and every stretch of each of them.

    A season is its own thing to ask browse for and a long one is answered a
    stretch at a time, so what is stored is every answer the show took, and only
    the stretch that begins a season says which season the ones after it are of.
    """

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                pages = not_yt_dlapi().shows.list_all(self.unique_identifier)
            except NotFoundError:
                self.write(None, f"Invalid unique_identifier {self.unique_identifier}")
            else:
                self.write([json.loads(page.raw) for page in pages])

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> list[ShowListingResponse]:
        return [ShowListingResponse.from_response(json.dumps(page)) for page in raw]

    # TODO: Validate
    def show_key(self) -> str | None:
        match = re.search(r"SC[A-Za-z0-9_-]{20,}", self.database_record.content or "")
        return match.group(0) if match else None

    # TODO: Validate
    def season_numbers(self) -> list[int]:
        return [season.number for season in get_first_item(self.parsed()).seasons]

    # TODO: Validate
    def episodes_by_season(self) -> dict[int, list[ShowEpisode]]:
        episodes: dict[int, list[ShowEpisode]] = {}
        season_number: int | None = None
        for page in self.parsed():
            if page.season is not None:
                season_number = page.season
            if season_number is None:
                continue
            episodes.setdefault(season_number, []).extend(page.episodes)
        return episodes


# TODO: Validate
class PlaylistFeed(XMLFile):
    """Playlist feed file."""

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            feed: FeedResponse
            try:
                if self.unique_identifier.startswith("UU"):
                    feed = not_yt_dlapi().channels.feed(
                        channel_id="UC" + self.unique_identifier[2:],
                    )
                else:
                    feed = not_yt_dlapi().playlists.feed(
                        playlist_id=self.unique_identifier,
                    )
            except HTTPError as error:
                logger.warning(
                    "PlaylistFeed fetch for {} returned HTTP {}; keeping the existing feed.",
                    self.unique_identifier,
                    error.status_code,
                )
                return
            self.write(feed.raw)

    # TODO: Validate
    def video_ids(self) -> list[str]:
        namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }
        result: list[str] = []
        for entry in self.parsed().findall("atom:entry", namespaces):
            video_id = entry.find("yt:videoId", namespaces)
            if video_id is not None and video_id.text:
                result.append(video_id.text)
        return result


# TODO: Validate
class ShowPage(HTMLFile):
    """Show page file.

    The API has no concept of a show, so a show and its seasons are read from the
    page YouTube serves for it.
    """

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        show_key: str,
    ) -> None:
        self.show_key = show_key
        super().__init__(session, plugin, show_key)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            response = get_around_client().get(
                f"https://www.youtube.com/show/{self.show_key}",
            )
            if not response.is_success:
                logger.warning(
                    "ShowPage fetch for {} returned HTTP {}; keeping the existing page.",
                    self.unique_identifier,
                    response.status_code,
                )
                return
            self.write(response.text)

    # TODO: Validate
    def _content(self) -> str:
        return self.database_record.content or ""

    # TODO: Validate
    def title(self) -> str | None:
        """Return the name of the show.

        The show's own title is the first one on the page; every later one belongs
        to an episode or a streaming service.
        """
        match = re.search(r'"title":\s*\{"simpleText":"([^"]+)"', self._content())
        return json.loads(f'"{match.group(1)}"') if match else None

    # TODO: Validate
    def playlist_key(self) -> str | None:
        match = re.search(r"TVSH[A-Za-z0-9_-]{20,}", self._content())
        return match.group(0) if match else None


# TODO: Validate
class FileMixin(BasePlugin, register=False):
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
    def music_playlist_file(self, playlist_key: str) -> MusicPlaylistFile:
        return self._file(MusicPlaylistFile, playlist_key)

    # TODO: Validate
    def topic_releases_file(self, channel_key: str) -> TopicReleasesFile:
        return self._file(TopicReleasesFile, channel_key)

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
        return bool(items) and items[0].snippet.title.endswith(" - Topic")

    # TODO: Validate
    def is_movies_channel(self, show_key: str) -> bool:
        if not is_channel_key(show_key):
            return False

        channel_file = self.channel_by_channel_id_file(show_key)
        if channel_file.is_outdated() or not channel_file.database_record.content:
            return False
        items = channel_file.parsed().items
        return bool(items) and items[0].snippet.title == "YouTube Movies"

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
    def topic_release_keys(self, channel_key: str) -> list[str]:
        """Return the playlist key of every release a Topic channel lists."""
        return [
            release.playlist_id
            for release in self.topic_releases_file(channel_key).parsed().releases
            if is_music_playlist_key(release.playlist_id)
        ]

    # TODO: Validate
    def show_season_numbers(self, show_key: str) -> list[str]:
        return [
            str(number)
            for number in self.show_listing_file_for_show(show_key).season_numbers()
        ]

    # TODO: Validate
    def show_episode_keys(self, show_key: str) -> list[str]:
        """Return the episode keys of every season of a show, in season order."""
        return self._episode_keys_from_file(
            self._season_keys_from_file(show_key),
            show_key,
        )

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # A show that is a single video is described by the video itself.
        if is_video_key(show_key):
            return [self.videos_file(show_key)]
        if is_music_playlist_key(show_key):
            return [self.music_playlist_file(show_key)]
        # A show has no API of its own, so its page lists its seasons.
        if is_show_key(show_key):
            # The page comes first because it is what names the playlist the
            # listing is asked for by.
            return [
                self.show_page_file(show_key),
                self.show_listing_file_for_show(show_key),
            ]
        # A Topic channel's releases are the only thing it lists, and the API says
        # nothing about them, so they are read off the channel's page instead of
        # out of the playlists it owns.
        if self.is_topic_channel(show_key):
            return [
                self.topic_releases_file(show_key),
                self.channel_by_channel_id_file(show_key),
            ]
        # A channel generated for one title has no seasons but its uploads, so what
        # it lists is never read.
        if self.is_movies_channel(show_key):
            return [self.channel_by_channel_id_file(show_key)]
        return [
            # Required to detect new seasons (playlists).
            self.channel_playlists_file(show_key),
            # ChannelByHandle is only used to get ChannelByChannelId so it is not used.
            # Required to detect changes to the show (channel).
            self.channel_by_channel_id_file(show_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # A season that is a single video is described by the video itself.
        if is_video_key(season_key):
            return [self.videos_file(season_key)]
        # A season of a show is described by the page for that season.
        if is_show_season_key(season_key):
            show_key, _ = split_show_season_key(season_key)
            return [self.show_listing_file_for_show(show_key)]
        if is_music_playlist_key(season_key):
            return [self.music_playlist_file(season_key)]
        return [
            # Required to detect new episodes (videos). Must stay first because
            # season_data_timestamp reads files[0].
            self.playlist_items_file(season_key),
            # Required to detect changes to the season (playlist).
            self.channel_playlists_file(show_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the episode (video).
        return [self.videos_file(episode_key)]

    # TODO: Validate
    def _video_is_valid(self, video_title: str) -> bool:
        """Check if a video is valid for importing."""
        return video_title not in ("Deleted video", "Private video")

    # TODO: Validate
    def channel_uploads_playlist_key(self, show_key: str) -> str:
        """Return the playlist ID for the channel's uploads."""
        return show_key[:1] + "U" + show_key[2:]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        # A show that is a single video has that video as its only season.
        if is_video_key(show_key):
            return [show_key]

        if is_music_playlist_key(show_key):
            return [show_key]

        # A show has one season for every season its page lists.
        if is_show_key(show_key):
            return [
                show_season_key(show_key, season_number)
                for season_number in self.show_season_numbers(show_key)
            ]

        # A Topic channel has one season for every release it lists.
        if self.is_topic_channel(show_key):
            return self._with_album_seasons(
                self.topic_release_keys(show_key),
                show_key,
            )

        channel_item = get_first_item(
            self.channel_by_channel_id_file(show_key).parsed().items,
        )
        season_keys: list[str] = []

        # If the channel has uploads also include that as a season. Generally, most
        # playlists consist of uploads from the channel so the channel should be the
        # first season_key listed so when the episodes are downloaded the channel
        # uploads are downloaded first because that will maximize the batch sizes and
        # minimize the number of API calls.
        if channel_item.statistics.video_count > 0:
            season_keys.append(self.channel_uploads_playlist_key(show_key))

        # A channel generated for one title of YouTube's catalogue is that title and
        # nothing else, so what it uploaded is all of it and what it lists besides is
        # not the title.
        if self.is_movies_channel(show_key):
            return season_keys

        channel_playlists_file = self.channel_playlists_file(show_key)
        if channel_playlists_file.database_record.content:
            season_keys.extend(
                item.id
                for item in channel_playlists_file.parsed().items
                if item.content_details.item_count > 0
            )

        return self._with_album_seasons(season_keys, show_key)

    # TODO: Validate
    def _with_album_seasons(self, season_keys: list[str], show_key: str) -> list[str]:
        # An album playlist is auto-generated and listed by no channel, so it is only
        # ever added by an importing URL naming it and then always kept.
        return season_keys + [
            key for key in self._album_season_keys(show_key) if key not in season_keys
        ]

    # TODO: Validate
    def _album_season_keys(self, show_key: str) -> list[str]:
        season_keys: list[str] = []
        if self._importing_album_playlist_key:
            season_keys.append(self._importing_album_playlist_key)

        existing_show = self._preload_show(show_key, preload_seasons=True).one_or_none()
        if existing_show:
            season_keys.extend(
                season.key
                for season in existing_show.seasons
                if is_music_playlist_key(season.key) and season.key not in season_keys
            )
        return season_keys

    # TODO: Validate
    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        # A channel generated for one title uploads that title once per language it
        # was published in, and every one of them is the same film, so the one
        # published here is the only one worth holding.
        usa_only = self.is_movies_channel(show_key)
        seen: set[str] = set()
        video_keys: list[str] = []
        for season_key in season_keys:
            for video_key in self._season_episode_keys(season_key):
                if video_key in seen:
                    continue
                if usa_only and not self.is_usa_video(video_key):
                    continue
                seen.add(video_key)
                video_keys.append(video_key)
        return video_keys

    # TODO: Validate
    def _season_episode_keys(self, season_key: str) -> list[str]:
        """Return the episode keys held by a single season."""
        # A season that is a single video holds only that video.
        if is_video_key(season_key):
            return [season_key]

        # A season of a show holds the episodes listed on its page.
        if is_show_season_key(season_key):
            show_key, season_number = split_show_season_key(season_key)
            episodes = self.show_listing_file_for_show(show_key).episodes_by_season()
            return [
                episode.video_id for episode in episodes.get(int(season_number), [])
            ]

        if is_music_playlist_key(season_key):
            return [
                track.video_id
                for track in self.music_playlist_file(season_key).parsed().tracks
            ]

        playlist_items_file = self.playlist_items_file(season_key)
        if not playlist_items_file.database_record.content:
            msg = (
                f"PlaylistItems file for season {season_key!r} has empty content "
                f"(file key {playlist_items_file.file_key()!r}, extra "
                f"{playlist_items_file.database_record.extra!r}). The playlist was "
                f"likely not found when downloaded."
            )
            raise ValueError(msg)
        return [
            item.content_details.video_id
            for item in playlist_items_file.parsed().items
            if self._video_is_valid(item.snippet.title)
        ]

    # TODO: Validate
    def _batch_download_videos(self, video_keys: list[str]) -> None:
        outdated_ids = [
            video_id
            for video_id in video_keys
            if self.videos_file(video_id).is_outdated()
        ]
        if not outdated_ids:
            return

        logger.info(f"Batch downloading {len(outdated_ids)} YouTube videos")
        start = time.monotonic()
        responses = not_yt_dlapi().videos.list_all(outdated_ids)
        elapsed_time = time.monotonic() - start
        logger.info(
            f"Batch downloaded {len(outdated_ids)} YouTube videos "
            f"in {elapsed_time:.2f}s",
        )

        responses_by_id: dict[str, str] = {
            response.items[0].id: response.raw for response in responses
        }
        for video_id in outdated_ids:
            video_file = self.videos_file(video_id)
            # write is called directly because of the way the files are batch downloaded.
            video_file.write(responses_by_id[video_id])

    # TODO: Validate
    @override
    def _download_show_files_and_children(
        self,
        show: str | Show,
        update_at: datetime | None = None,
    ) -> list[File]:
        """Read the channel before the files that depend on what it is.

        Which files describe a channel is not the same for a Topic channel as for
        any other, and only the channel says which it is, so it is read before
        anything asks.
        """
        show_key = self._get_key(show)
        if is_channel_key(show_key):
            self.channel_by_channel_id_file(show_key).download_if_outdated(update_at)
        # The page names the playlist the show's listing is asked for by, so the
        # files a show has cannot be named until it has been read.
        if is_show_key(show_key):
            self.show_page_file(show_key).download_if_outdated(update_at)
        return super()._download_show_files_and_children(show, update_at)

    # TODO: Validate
    @override
    def _download_all_season_files(self, show: str | Show) -> list[File]:
        """Batch download the videos of every playlist in a single API call."""
        show_key = self._get_key(show)
        season_keys = self._season_keys_from_file(show_key)
        _cache = self._preload_season_files(season_keys, show_key)
        all_files: list[File] = []
        for season_key in season_keys:
            season_files = self._season_files(season_key, show_key)
            all_files.extend(self._download_outdated_files(season_files))

        episode_cache = self._preload_all_episode_files(season_keys, show_key)
        self._batch_download_videos(
            self._episode_keys_from_file(season_keys, show_key),
        )
        for season_key in season_keys:
            all_files.extend(
                self._download_all_episode_files(
                    season_key,
                    show_key,
                    preloaded_files=episode_cache,
                ),
            )
        return all_files

    # TODO: Validate
    @override
    def _download_all_episode_files(
        self,
        season: str | Season,
        show: str | Show | None = None,
        preloaded_files: Sequence[File] | None = None,
    ) -> list[File]:
        """Batch download all videos for a season in a single API call."""
        season_key = self._get_key(season)
        show_key = self._get_show_key(season, show)
        video_keys = self._episode_keys_from_file(season_key, show_key)
        self._preload_episode_files(video_keys, season_key, show_key, preloaded_files)
        self._batch_download_videos(video_keys)
        return [self.videos_file(video_id).database_record for video_id in video_keys]
