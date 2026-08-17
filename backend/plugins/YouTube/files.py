# TODO: Validate
import json
import re
import time
from collections.abc import Sequence
from datetime import timedelta
from functools import cache
from typing import Any, cast, override
from urllib.parse import parse_qs, urlparse

from loguru import logger
from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.channel import Channel as ChannelEndpoint
from not_yt_dlapi.channel.models import ChannelsModel
from not_yt_dlapi.exceptions import (
    ChannelNotFoundError,
    NotYTDLAPIError,
    PlaylistNotFoundError,
)
from not_yt_dlapi.playlist_item import PlaylistItems as PlaylistItemsEndpoint
from not_yt_dlapi.playlist_item.models import PlaylistItemsModel
from not_yt_dlapi.playlists import Playlists as PlaylistsEndpoint
from not_yt_dlapi.playlists.models import PlaylistsModel
from not_yt_dlapi.video.models import VideosModel
from sqlmodel import Session

from app.config import settings
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    GAPIJSON,
    BaseFile,
    GAPIJSONNoGet,
    HTMLFile,
    XMLFile,
)
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def not_yt_dlapi() -> NotYTDLAPI:
    return NotYTDLAPI(
        api_key=settings.YOUTUBE_API_KEY,
        get_around_client=get_around_client(),
    )


# TODO: Validate
def is_music_playlist_key(key: str) -> bool:
    """Report whether a playlist key belongs to an auto-generated album."""
    return key.startswith("OLAK5uy_")


# The official YouTube Movies & TV channel. Its uploads playlist and playlist listing
# are truncated, so most of the videos it owns are missing from every listing the
# channel exposes and can only be reached by importing them one at a time.
_STANDALONE_VIDEO_CHANNEL_KEYS = frozenset({"UCuVPpxrm2VAgpH3Ktln4HXg"})


# TODO: Validate
def is_standalone_video_channel(channel_key: str) -> bool:
    """Report whether a channel's videos are imported one video at a time.

    A video from such a channel becomes a show of its own instead of an episode of
    the channel, so importing one only ever adds the video that was asked for.
    """
    return channel_key in _STANDALONE_VIDEO_CHANNEL_KEYS


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


# The reasons YouTube gives when the API key has spent its daily quota. The quota
# resets at midnight Pacific Time, so nothing else will succeed until then.
_QUOTA_REASONS = frozenset({"dailyLimitExceeded", "quotaExceeded"})


# TODO: Validate
def is_quota_error(error: BaseException) -> bool:
    """Report whether `error` is the YouTube API refusing calls until quota resets."""
    if not isinstance(error, NotYTDLAPIError):
        return False
    errors = error.response.get("error", {}).get("errors", [])
    return any(item.get("reason") in _QUOTA_REASONS for item in errors)


# TODO: Validate
def get_first_item[T](items: list[T] | None) -> T:
    if not items:
        msg = "Expected at least one item, got none"
        raise ValueError(msg)
    return items[0]


# TODO: Validate
def _merge_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge paginated API responses into a single response with all items."""
    merged = dict(pages[0])
    merged["items"] = [item for page in pages for item in page.get("items", [])]
    return merged


# TODO: Validate
class ChannelByChannelId(GAPIJSONNoGet[ChannelsModel]):
    """Channel by channel ID file."""

    API_ENDPOINT = not_yt_dlapi().channel

    # TODO: Validate
    @override
    def _get(self) -> ChannelsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, ChannelEndpoint)
        return endpoint.download_and_parse(channel_id=self.unique_identifier)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ChannelNotFoundError)


# TODO: Validate
class ChannelByHandle(GAPIJSONNoGet[ChannelsModel]):
    """Channel by handle file."""

    API_ENDPOINT = not_yt_dlapi().channel

    # TODO: Validate
    @override
    def _get(self) -> ChannelsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, ChannelEndpoint)
        return endpoint.download_and_parse(channel_handle=self.unique_identifier)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ChannelNotFoundError)


# TODO: Validate
class ChannelByUsername(GAPIJSONNoGet[ChannelsModel]):
    """Channel by username file."""

    API_ENDPOINT = not_yt_dlapi().channel

    # TODO: Validate
    @override
    def _get(self) -> ChannelsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, ChannelEndpoint)
        return endpoint.download_and_parse(channel_username=self.unique_identifier)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ChannelNotFoundError)


# TODO: Validate
class ChannelPlaylists(GAPIJSONNoGet[PlaylistsModel]):
    """Channel playlists file."""

    API_ENDPOINT = not_yt_dlapi().playlists

    # TODO: Validate
    @override
    def _get(self) -> PlaylistsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, PlaylistsEndpoint)
        return endpoint.parse(
            _merge_pages(endpoint.download_all(self.unique_identifier)),
        )

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ChannelNotFoundError)


# TODO: Validate
class PlaylistInfo(GAPIJSONNoGet[PlaylistsModel]):
    """Playlist info file."""

    API_ENDPOINT = not_yt_dlapi().playlists

    # TODO: Validate
    @override
    def _get(self) -> PlaylistsModel:
        endpoint = self.raise_if_not_is_instance(self.API_ENDPOINT, PlaylistsEndpoint)
        return endpoint.download_and_parse(playlist_id=self.unique_identifier)


# TODO: Validate
class PlaylistItems(GAPIJSONNoGet[PlaylistItemsModel]):
    """Playlist items file."""

    API_ENDPOINT = not_yt_dlapi().playlist_items

    # Due to API limits this function merges new videos with existing videos instead of
    # downloading all videos every time.
    # TODO: Validate
    @override
    def _get(self) -> PlaylistItemsModel:
        endpoint = self.raise_if_not_is_instance(
            self.API_ENDPOINT,
            PlaylistItemsEndpoint,
        )

        # If this is the first time downloading the file download everything.
        if not self._existing_database_record:
            return endpoint.parse(
                _merge_pages(endpoint.download_all_pages(self.unique_identifier)),
            )

        # If the entry is over a year old download a fresh non-canonical row to clean
        # out deleted videos. Album playlists are auto-generated and never change, so
        # re-paging them would spend quota to rediscover the same tracks.
        year_ago_datetime = tz_datetime.now() - timedelta(days=365)
        if (
            not is_music_playlist_key(self.unique_identifier)
            and self._existing_database_record.data_timestamp < year_ago_datetime
        ):
            return endpoint.parse(
                _merge_pages(endpoint.download_all_pages(self.unique_identifier)),
            )

        existing_items: list[dict[str, Any]] = json.loads(
            self.database_record.content or "{}",
        )["items"]
        existing_video_ids = {
            item["contentDetails"]["videoId"] for item in existing_items
        }

        pages: list[dict[str, Any]] = []
        page_token: str | None = None
        reached_existing_video = False
        while not reached_existing_video:
            page = endpoint.download(self.unique_identifier, page_token=page_token)
            pages.append(page)
            # Everything from the first already stored video onwards is already stored,
            # so the remaining pages do not need to be spent on.
            reached_existing_video = any(
                item["contentDetails"]["videoId"] in existing_video_ids
                for item in page["items"]
            )
            page_token = page.get("nextPageToken")
            if not page_token:
                break

        merged = _merge_pages(pages)
        # Paging to the end of the playlist without reaching a stored video means the
        # download covers the whole playlist, so keeping the stored items would keep
        # videos that have since been removed.
        if not reached_existing_video:
            return endpoint.parse(merged)

        new_ids = {item["contentDetails"]["videoId"] for item in merged["items"]}
        merged["items"] = merged["items"] + [
            item
            for item in existing_items
            if item["contentDetails"]["videoId"] not in new_ids
        ]
        return endpoint.parse(merged)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, PlaylistNotFoundError)


# TODO: Validate
class Videos(GAPIJSON[VideosModel]):
    """Videos file."""

    API_ENDPOINT = not_yt_dlapi().videos


# TODO: Validate
class PlaylistFeed(XMLFile):
    """Playlist feed file."""

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            if self.unique_identifier.startswith("UU"):
                params = {"channel_id": "UC" + self.unique_identifier[2:]}
            else:
                params = {"playlist_id": self.unique_identifier}
            response = get_around_client().get(
                "https://www.youtube.com/feeds/videos.xml",
                params=params,
            )
            if not response.is_success:
                logger.warning(
                    "PlaylistFeed fetch for {} returned HTTP {}; keeping the existing feed.",
                    self.unique_identifier,
                    response.status_code,
                )
                return
            self.write(response.text)

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
def _find_renderer(node: object, name: str) -> dict[str, Any] | None:
    """Return the first renderer called `name` anywhere in the page data."""
    if isinstance(node, dict):
        contents = cast("dict[str, Any]", node)
        renderer = contents.get(name)
        if isinstance(renderer, dict):
            return cast("dict[str, Any]", renderer)
        for value in contents.values():
            if found := _find_renderer(value, name):
                return found
    elif isinstance(node, list):
        values: list[Any] = node
        for value in values:
            if found := _find_renderer(value, name):
                return found
    return None


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
        season_number: str | None = None,
    ) -> None:
        self.show_key = show_key
        self.season_number = season_number
        identifier = (
            show_key if season_number is None else f"{show_key}/{season_number}"
        )
        super().__init__(session, plugin, identifier)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            params = (
                {} if self.season_number is None else {"season": self.season_number}
            )
            response = get_around_client().get(
                f"https://www.youtube.com/show/{self.show_key}",
                params=params,
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
    def _initial_data(self) -> dict[str, Any]:
        match = re.search(r"var ytInitialData = (\{.*?\});</script>", self._content())
        if not match:
            msg = f"Show page {self.unique_identifier} has no page data."
            raise ValueError(msg)
        return cast("dict[str, Any]", json.loads(match.group(1)))

    # TODO: Validate
    def title(self) -> str | None:
        """Return the name of the show.

        The show's own title is the first one on the page; every later one belongs
        to an episode or a streaming service.
        """
        match = re.search(r'"title":\s*\{"simpleText":"([^"]+)"', self._content())
        return json.loads(f'"{match.group(1)}"') if match else None

    # TODO: Validate
    def season_numbers(self) -> list[str]:
        """Return the season numbers the show lists, in the order it lists them."""
        sub_menu = _find_renderer(self._initial_data(), "sortFilterSubMenuRenderer")
        if not sub_menu:
            return []

        season_numbers: list[str] = []
        for item in sub_menu.get("subMenuItems", []):
            url: str = item["navigationEndpoint"]["commandMetadata"][
                "webCommandMetadata"
            ]["url"]
            season = parse_qs(urlparse(url).query).get("season", [])
            if season and season[0] not in season_numbers:
                season_numbers.append(season[0])
        return season_numbers

    # TODO: Validate
    def episode_keys(self) -> list[str]:
        """Return the video keys of the episodes of the season this page shows."""
        video_list = _find_renderer(self._initial_data(), "playlistVideoListRenderer")
        if not video_list:
            return []

        episode_keys: list[str] = []
        for content in video_list.get("contents", []):
            video = content.get("playlistVideoRenderer")
            if video and video["videoId"] not in episode_keys:
                episode_keys.append(video["videoId"])
        return episode_keys


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    _importing_album_playlist_key: str | None = None

    # TODO: Validate
    def channel_by_channel_id_file(self, show_key: str) -> ChannelByChannelId:
        """Return a cached ChannelByChannelId for the given show key."""
        return self._file(ChannelByChannelId, show_key)

    # TODO: Validate
    def channel_by_handle_file(self, channel_handle: str) -> ChannelByHandle:
        """Return a cached ChannelByHandle for the given channel handle."""
        return self._file(ChannelByHandle, channel_handle)

    # TODO: Validate
    def channel_by_username_file(self, channel_username: str) -> ChannelByUsername:
        """Return a cached ChannelByUsername for the given channel username."""
        return self._file(ChannelByUsername, channel_username)

    # TODO: Validate
    def channel_playlists_file(self, show_key: str) -> ChannelPlaylists:
        """Return a cached ChannelPlaylists for the given show key."""
        return self._file(ChannelPlaylists, show_key)

    # TODO: Validate
    def playlist_info_file(self, playlist_key: str) -> PlaylistInfo:
        """Return a cached PlaylistInfo for the given playlist key."""
        return self._file(PlaylistInfo, playlist_key)

    # TODO: Validate
    def playlist_items_file(self, season_key: str) -> PlaylistItems:
        """Return a cached PlaylistItems for the given season key."""
        return self._file(PlaylistItems, season_key)

    # TODO: Validate
    def videos_file(self, episode_key: str) -> Videos:
        """Return a cached Videos for the given episode key."""
        return self._file(Videos, episode_key)

    # TODO: Validate
    def playlist_feed_file(self, season_key: str) -> PlaylistFeed:
        """Return a cached PlaylistFeed for the given season key."""
        return self._file(PlaylistFeed, season_key)

    # TODO: Validate
    def show_page_file(
        self,
        show_key: str,
        season_number: str | None = None,
    ) -> ShowPage:
        """Return a cached ShowPage for the given show key and season."""
        return self._file(ShowPage, show_key, season_number)

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
        # A show has no API of its own, so its page lists its seasons.
        if is_show_key(show_key):
            return [self.show_page_file(show_key)]
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
            return [self.show_page_file(*split_show_season_key(season_key))]
        files: list[ChannelPlaylists | PlaylistItems | PlaylistInfo] = [
            # Required to detect new episodes (videos). Must stay first because
            # season_data_timestamp reads files[0].
            self.playlist_items_file(season_key),
            # Required to detect changes to the season (playlist).
            self.channel_playlists_file(show_key),
        ]
        # Album playlists are auto-generated and not listed by the channel, so the album
        # name comes from the playlist itself rather than the channel playlists file.
        if is_music_playlist_key(season_key):
            files.append(self.playlist_info_file(season_key))
        return files

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

        # A show has one season for every season its page lists.
        if is_show_key(show_key):
            show_page = self.show_page_file(show_key)
            return [
                show_season_key(show_key, season_number)
                for season_number in show_page.season_numbers()
            ]

        channel_item = get_first_item(
            self.channel_by_channel_id_file(show_key).parsed().items,
        )
        season_keys: list[str] = []

        # If the channel has uploads also include that as a season. Generally, most
        # playlists consist of uploads from the channel so the channel should be the
        # first season_key listed so when the episodes are downloaded the channel
        # uploads are downloaded first because that will maximize the batch sizes and
        # minimize the number of API calls.
        if int(channel_item.statistics.video_count) > 0:
            season_keys.append(self.channel_uploads_playlist_key(show_key))

        channel_playlists_file = self.channel_playlists_file(show_key)
        if channel_playlists_file.database_record.content:
            season_keys.extend(
                item.id
                for item in channel_playlists_file.parsed().items
                if item.content_details.item_count > 0
            )

        # Album playlists are auto-generated and not returned by any channel listing, so
        # they are only ever added by an explicit import and then always kept.
        season_keys.extend(
            key for key in self._album_season_keys(show_key) if key not in season_keys
        )

        return season_keys

    # TODO: Validate
    def _album_season_keys(self, show_key: str) -> list[str]:
        season_keys: list[str] = []
        if self._importing_album_playlist_key:
            season_keys.append(self._importing_album_playlist_key)
        existing_show = self._preload_show(
            show_key,
            preload_seasons=True,
        ).one_or_none()
        if existing_show:
            for season in existing_show.seasons:
                if (
                    season.deleted_at is None
                    and is_music_playlist_key(season.key)
                    and season.key not in season_keys
                ):
                    season_keys.append(season.key)
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
        seen: set[str] = set()
        video_keys: list[str] = []
        for season_key in season_keys:
            for video_key in self._season_episode_keys(season_key):
                if video_key not in seen:
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
            show_page = self.show_page_file(*split_show_season_key(season_key))
            return show_page.episode_keys()

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

        outdated_ids = [
            video_id
            for video_id in video_keys
            if self.videos_file(video_id).is_outdated()
        ]

        if outdated_ids:
            logger.info(f"Batch downloading {len(outdated_ids)} YouTube videos")
            start = time.monotonic()
            pages = not_yt_dlapi().videos.download_all(outdated_ids)
            elapsed_time = time.monotonic() - start
            logger.info(
                f"Batch downloaded {len(outdated_ids)} YouTube videos "
                f"in {elapsed_time:.2f}s",
            )

            responses_by_id: dict[str, dict[str, Any]] = {
                item["id"]: {**page, "items": [item]}
                for page in pages
                for item in page.get("items", [])
            }
            for video_id in outdated_ids:
                video_file = self.videos_file(video_id)
                # write is called directly because of the way the files are batch downloaded.
                video_file.write(json.dumps(responses_by_id[video_id], default=str))

        return [self.videos_file(video_id).database_record for video_id in video_keys]
