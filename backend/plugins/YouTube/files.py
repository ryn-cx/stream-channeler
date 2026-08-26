# TODO: Validate
import json
import re
import time
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, ClassVar, override
from urllib.parse import parse_qs, urlsplit

from loguru import logger
from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.channel_feed.models import ChannelFeedModel
from not_yt_dlapi.channels import Channels as ChannelsEndpoint
from not_yt_dlapi.channels.models import ChannelsModel
from not_yt_dlapi.exceptions import (
    APIError,
    ChannelFeedNotFoundError,
    PlaylistFeedNotFoundError,
    ResourceNotFoundError,
)
from not_yt_dlapi.music import Music as MusicEndpoint
from not_yt_dlapi.music.models import LockupViewModel as MusicLockupViewModel
from not_yt_dlapi.music.models import MusicModel
from not_yt_dlapi.music.models import PlaylistHeaderRenderer as MusicHeaderRenderer
from not_yt_dlapi.playlist_feed.models import PlaylistFeedModel
from not_yt_dlapi.playlist_items import PlaylistItems as PlaylistItemsEndpoint
from not_yt_dlapi.playlist_items.models import Item, PlaylistItemsModel
from not_yt_dlapi.playlists import Playlists as PlaylistsEndpoint
from not_yt_dlapi.playlists.models import PlaylistsModel
from not_yt_dlapi.shows import Shows as ShowsEndpoint
from not_yt_dlapi.shows.models import ShowsModel
from not_yt_dlapi.topic import Topic as TopicEndpoint
from not_yt_dlapi.topic.models import TopicModel
from not_yt_dlapi.videos import Videos as VideosEndpoint
from not_yt_dlapi.videos.models import VideosModel
from sqlmodel import Session

from app.config import settings
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    BaseFile,
    EndpointFile,
    HTMLFile,
    LoadEndpoint,
    PagedEndpointFile,
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
def is_an_album(key: str) -> bool:
    return key.startswith("OLAK5uy_")


# TODO: Validate
def is_channel_key(key: str) -> bool:
    """Report whether a key belongs to a channel rather than to what one holds."""
    return not (
        is_video_key(key)
        or is_show_key(key)
        or is_an_album(key)
        or is_user_playlist(key)
    )


# TODO: Validate
def is_user_playlist(key: str) -> bool:
    return key.startswith("PL")


# TODO: Validate
def is_free_movies_channel(channel_key: str) -> bool:
    """Report whether a channel is the one YouTube's free catalogue is published on.

    Everything YouTube serves free with ads is owned by this one channel, and a
    title that has to be bought or rented is owned by a channel generated for
    that title alone, so who owns a video is what says which of the two it is.
    """
    return channel_key == "UCuVPpxrm2VAgpH3Ktln4HXg"


# TODO: Validate
def is_video_key(key: str) -> bool:
    """Return whether a  is for a video.

    Show.key and Season.key is a video key if it is a free movie."""
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
def is_regular_playlist(key: str) -> bool:
    return key.startswith("PL") or is_channel_uploads_playlist_key(key)


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
    errors = error.error.get("errors", [])
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
class ChannelByChannelId(EndpointFile[ChannelsModel]):
    API_ENDPOINT: ClassVar[ChannelsEndpoint] = not_yt_dlapi().channels

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(channel_id=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class ChannelByHandle(EndpointFile[ChannelsModel]):
    API_ENDPOINT: ClassVar[ChannelsEndpoint] = not_yt_dlapi().channels

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(channel_handle=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class ChannelByUsername(EndpointFile[ChannelsModel]):
    API_ENDPOINT: ClassVar[ChannelsEndpoint] = not_yt_dlapi().channels

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(channel_username=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class ChannelPlaylists(EndpointFile[PlaylistsModel]):
    API_ENDPOINT: ClassVar[PlaylistsEndpoint] = not_yt_dlapi().playlists

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download_merged(channel_id=self.unique_identifier)


# TODO: Validate
class PlaylistInfo(EndpointFile[PlaylistsModel]):
    API_ENDPOINT: ClassVar[PlaylistsEndpoint] = not_yt_dlapi().playlists

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(playlist_ids=self.unique_identifier)


# TODO: Validate
class PlaylistItems(EndpointFile[PlaylistItemsModel]):
    """Playlist items file."""

    API_ENDPOINT: ClassVar[PlaylistItemsEndpoint] = not_yt_dlapi().playlist_items

    # TODO: Validate
    def items(self) -> list[Item]:
        """Return the items the file holds."""
        return self.parsed().items

    # Due to API limits this function merges new videos with existing videos instead of
    # downloading all videos every time which over time will lead to a messy file with
    # dead videos.
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # If this is the first time downloading the file download all of the pages.
        if not self._existing_database_record:
            return self.API_ENDPOINT.download_merged(self.unique_identifier)

        pages: list[str] = []
        page_token: str | None = None
        reached_existing_video = False
        downloaded_all_pages = False
        while not (reached_existing_video or downloaded_all_pages):
            downloaded_page = self.API_ENDPOINT.download(
                self.unique_identifier,
                page_token=page_token,
            )
            pages.append(downloaded_page)
            loaded_page = self.API_ENDPOINT.load(downloaded_page)
            page_token = loaded_page.next_page_token
            downloaded_all_pages = page_token is None

            reached_existing_video = any(
                item.snippet.published_at < self.data_timestamp
                for item in loaded_page.items
            )

        if downloaded_all_pages:
            return self.API_ENDPOINT.merge_pages(pages)
        return self._merged_items(pages, self._remove_deleted_items(pages))

    # TODO: Validate
    def _remove_deleted_items(self, pages: list[str]) -> list[dict[str, Any]]:
        downloaded_video_ids = self._downloaded_video_ids(pages)
        stored_items: list[dict[str, Any]] = json.loads(self._stored_content())["items"]
        kept_from = max(
            (
                index + 1
                for index, item in enumerate(stored_items)
                if item["contentDetails"]["videoId"] in downloaded_video_ids
            ),
            default=0,
        )
        return stored_items[kept_from:]

    # TODO: Validate
    def _downloaded_video_ids(self, pages: list[str]) -> set[str]:
        return {
            item["contentDetails"]["videoId"]
            for page in pages
            for item in json.loads(page)["items"]
        }

    # TODO: Validate
    def _merged_items(
        self,
        pages: list[str],
        kept_items: list[dict[str, Any]],
    ) -> str:
        downloaded_video_ids = self._downloaded_video_ids(pages)
        items = [item for page in pages for item in json.loads(page)["items"]] + [
            item
            for item in kept_items
            if item["contentDetails"]["videoId"] not in downloaded_video_ids
        ]

        for position, item in enumerate(items):
            item["snippet"]["position"] = position

        # Use pages[0] as the base because it has the correct value for
        # .page_info.total_results.
        document = json.loads(pages[0])
        document["items"] = items
        document.pop("nextPageToken", None)
        document.pop("prevPageToken", None)
        return json.dumps(document)


# TODO: Validate
class Videos(EndpointFile[VideosModel]):
    API_ENDPOINT: ClassVar[VideosEndpoint] = not_yt_dlapi().videos


# TODO: Validate
class MusicPlaylistFile(EndpointFile[MusicModel]):
    API_ENDPOINT: ClassVar[MusicEndpoint] = not_yt_dlapi().music

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # TODO: Validate
    def _header(self) -> MusicHeaderRenderer:
        return self.parsed().header.playlist_header_renderer

    # The subtitle reads "Future, Metro Boomin • Album", so the names are what comes
    # before the bullet the release type is written after.
    # TODO: Validate
    def _credit(self) -> tuple[str, str]:
        credit, _, release_type = self._header().subtitle.simple_text.rpartition(
            " \u2022 ",
        )
        return credit, release_type

    # TODO: Validate
    def title(self) -> str | None:
        return self._header().title.simple_text

    # TODO: Validate
    def artists(self) -> list[str]:
        credit, _ = self._credit()
        return [name.strip() for name in credit.split(",")] if credit else []

    # TODO: Validate
    def release_type(self) -> str | None:
        credit, release_type = self._credit()
        if not credit:
            return release_type or None
        return release_type

    # TODO: Validate
    def _track_lockups(self) -> list[MusicLockupViewModel]:
        return [
            item.lockup_view_model
            for tab in self.parsed().contents.two_column_browse_results_renderer.tabs
            for section in tab.tab_renderer.content.section_list_renderer.contents
            for item in section.item_section_renderer.contents
            if item.lockup_view_model.content_type == "LOCKUP_CONTENT_TYPE_VIDEO"
        ]

    # TODO: Validate
    def track_keys(self) -> list[str]:
        return [lockup.content_id for lockup in self._track_lockups()]

    # TODO: Validate
    def image_url(self) -> str | None:
        images = self._header().playlist_header_banner.hero_playlist_thumbnail_renderer.thumbnail.thumbnails
        return images[-1].url if images else None

    # TODO: Validate
    def artist_channel_id(self) -> str | None:
        channel_keys = Counter(
            lockup.metadata.lockup_metadata_view_model.image.decorated_avatar_view_model.renderer_context.command_context.on_tap.innertube_command.browse_endpoint.browse_id
            for lockup in self._track_lockups()
        )
        return next((channel for channel, _ in channel_keys.most_common(1)), None)


# TODO: Validate
class TopicReleasesFile(PagedEndpointFile[TopicModel]):
    """The albums and singles a musician's Topic channel lists.

    The channel lists a dozen releases on a shelf and the rest behind it, and a
    shelf release is listed again by the first page behind it, so the pages are
    stored as they were served and read back as one listing with each release
    named once.
    """

    API_ENDPOINT: ClassVar[TopicEndpoint] = not_yt_dlapi().topic

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # The shelf a channel opens with writes its releases in a list of its own and
    # the panel behind it writes them into a grid, so both are read.
    # TODO: Validate
    def _page_release_keys(self, page: TopicModel) -> list[str]:
        endpoints = page.on_response_received_endpoints
        if endpoints is not None:
            return [
                grid_item.grid_playlist_renderer.playlist_id
                for endpoint in endpoints
                for continuation_item in (
                    endpoint.append_continuation_items_action.continuation_items
                )
                if continuation_item.grid_renderer is not None
                for grid_item in continuation_item.grid_renderer.items
                if grid_item.grid_playlist_renderer is not None
            ]

        contents = page.contents
        if contents is None:
            return []
        return [
            shelf_item.lockup_view_model.content_id
            for tab in contents.two_column_browse_results_renderer.tabs
            for section in tab.tab_renderer.content.section_list_renderer.contents
            for item in section.item_section_renderer.contents
            for shelf_item in (
                item.shelf_renderer.content.horizontal_list_renderer.items
            )
        ]

    # TODO: Validate
    def release_keys(self) -> list[str]:
        keys: list[str] = []
        for page in self.parsed():
            for key in self._page_release_keys(page):
                if key not in keys:
                    keys.append(key)
        return keys


# TODO: Validate
class ShowListing(PagedEndpointFile[ShowsModel]):
    """Every season of a show and every stretch of each of them.

    A season is its own thing to ask browse for and a long one is answered a
    stretch at a time, so what is stored is every answer the show took, and only
    the stretch that begins a season says which season the ones after it are of.
    """

    API_ENDPOINT: ClassVar[ShowsEndpoint] = not_yt_dlapi().shows

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # TODO: Validate
    def show_key(self) -> str | None:
        match = re.search(r"SC[A-Za-z0-9_-]{20,}", self.database_record.content or "")
        return match.group(0) if match else None

    # TODO: Validate
    def offer_labels(self) -> set[str]:
        return {
            badge.metadata_badge_renderer.label
            for page in self.parsed()
            if page.sidebar is not None
            for item in page.sidebar.playlist_sidebar_renderer.items
            if item.playlist_sidebar_primary_info_renderer.badges is not None
            for badge in item.playlist_sidebar_primary_info_renderer.badges
            if badge.metadata_badge_renderer.style == "BADGE_STYLE_TYPE_YPC"
        }

    # TODO: Validate
    def season_numbers(self) -> list[int]:
        return sorted(self.episode_keys_by_season())

    # A season is chosen from the same menu a playlist is sorted from, so what tells
    # the two apart is that a season says which season it is, and it says so in the
    # address a person would read it at rather than in the endpoint browse is asked
    # by.
    # TODO: Validate
    def _open_season(self, page: ShowsModel) -> int | None:
        if page.contents is None:
            return None
        for tab in page.contents.two_column_browse_results_renderer.tabs:
            for section in tab.tab_renderer.content.section_list_renderer.contents:
                for item in section.item_section_renderer.contents:
                    metadata = item.playlist_show_metadata_renderer
                    if metadata is None:
                        continue
                    for menu_item in (
                        metadata.collection.sort_filter_sub_menu_renderer.sub_menu_items
                    ):
                        if not menu_item.selected:
                            continue
                        query = urlsplit(
                            menu_item.navigation_endpoint.command_metadata.web_command_metadata.url,
                        ).query
                        numbers = parse_qs(query).get("season", ())
                        if numbers and numbers[0].isdigit():
                            return int(numbers[0])
        return None

    # TODO: Validate
    def _page_episode_keys(self, page: ShowsModel) -> list[str]:
        if page.contents is None:
            return []
        return [
            content.playlist_video_renderer.video_id
            for tab in page.contents.two_column_browse_results_renderer.tabs
            for section in tab.tab_renderer.content.section_list_renderer.contents
            for item in section.item_section_renderer.contents
            if item.playlist_video_list_renderer is not None
            for content in item.playlist_video_list_renderer.contents
        ]

    # TODO: Validate
    def episode_keys_by_season(self) -> dict[int, list[str]]:
        episode_keys: dict[int, list[str]] = {}
        season_number: int | None = None
        for page in self.parsed():
            open_season = self._open_season(page)
            if open_season is not None:
                season_number = open_season
            if season_number is None:
                continue
            episode_keys.setdefault(season_number, []).extend(
                self._page_episode_keys(page),
            )
        return episode_keys


# TODO: Validate
class PlaylistFeed(EndpointFile[ChannelFeedModel | PlaylistFeedModel]):
    """Playlist feed file."""

    # TODO: Validate
    def _is_channel_feed(self) -> bool:
        return self.unique_identifier.startswith("UU")

    # TODO: Validate
    @override
    def _load_endpoint(self) -> LoadEndpoint[ChannelFeedModel | PlaylistFeedModel]:
        if self._is_channel_feed():
            return not_yt_dlapi().channel_feed
        return not_yt_dlapi().playlist_feed

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".xml"

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        if self._is_channel_feed():
            return not_yt_dlapi().channel_feed.download(
                "UC" + self.unique_identifier[2:],
            )
        return not_yt_dlapi().playlist_feed.download(self.unique_identifier)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                feed = self._download_file()
            except (ChannelFeedNotFoundError, PlaylistFeedNotFoundError) as error:
                logger.warning(
                    "PlaylistFeed fetch for {} returned HTTP {}; keeping the existing feed.",
                    self.unique_identifier,
                    error.status_code,
                )
                return
            self.write(feed)

    # TODO: Validate
    def video_ids(self) -> list[str]:
        return [entry.video_id for entry in self.parsed().entry]


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
    _linking_playlist_key: str | None = None

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
            release_key
            for release_key in self.topic_releases_file(channel_key).release_keys()
            if is_an_album(release_key)
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
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:  # noqa: PLR0911
        if is_video_key(show_key):
            return [self.videos_file(show_key)]
        if is_an_album(show_key):
            return [self.music_playlist_file(show_key)]
        if is_user_playlist(show_key):
            return [self.playlist_info_file(show_key)]
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
        if is_an_album(season_key):
            return [self.music_playlist_file(season_key)]
        if is_user_playlist(show_key):
            return [
                self.playlist_items_file(season_key),
                self.playlist_info_file(show_key),
            ]
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

        if is_an_album(show_key) or is_user_playlist(show_key):
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
        if int(channel_item.statistics.video_count) > 0:
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
                if is_an_album(season.key) and season.key not in season_keys
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
            episode_keys = self.show_listing_file_for_show(
                show_key,
            ).episode_keys_by_season()
            return episode_keys.get(int(season_number), [])

        if is_an_album(season_key):
            return self.music_playlist_file(season_key).track_keys()

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
        responses = not_yt_dlapi().videos.download_all(outdated_ids)
        elapsed_time = time.monotonic() - start
        logger.info(
            f"Batch downloaded {len(outdated_ids)} YouTube videos "
            f"in {elapsed_time:.2f}s",
        )

        # A batch answers for fifty videos at once and every video is stored in a
        # file of its own, so each item is written out as the response it would
        # have arrived in had it been asked for on its own.
        responses_by_id: dict[str, str] = {}
        for response in responses:
            page: dict[str, Any] = json.loads(response)
            for item in page["items"]:
                responses_by_id[item["id"]] = json.dumps({**page, "items": [item]})
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
