# TODO: Validate
import json
import re
from collections import Counter
from functools import cache
from typing import Any, override
from urllib.parse import parse_qs, urlsplit

from loguru import logger
from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.channel_feed.models import ChannelFeedModel
from not_yt_dlapi.channels import Channels as ChannelsEndpoint
from not_yt_dlapi.channels.models import ChannelsModel
from not_yt_dlapi.exceptions import (
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
from app.plugins.models import Plugin
from plugins.utils.base_plugin_v3.files import (
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
class ChannelByChannelId(EndpointFile[ChannelsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ChannelsEndpoint:
        return not_yt_dlapi().channels

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(channel_id=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class ChannelByHandle(EndpointFile[ChannelsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ChannelsEndpoint:
        return not_yt_dlapi().channels

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(channel_handle=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class ChannelByUsername(EndpointFile[ChannelsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ChannelsEndpoint:
        return not_yt_dlapi().channels

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(channel_username=self.unique_identifier)

    # Occurs when importing an invalid channel URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class ChannelPlaylists(EndpointFile[PlaylistsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> PlaylistsEndpoint:
        return not_yt_dlapi().playlists

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download_merged(channel_id=self.unique_identifier)

    # TODO: Validate
    def has_only_uploads(self) -> bool:
        if not self.database_record.content:
            return True
        return not any(
            item.content_details.item_count > 0 for item in self.parsed().items
        )


# TODO: Validate
class PlaylistInfo(EndpointFile[PlaylistsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> PlaylistsEndpoint:
        return not_yt_dlapi().playlists

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(playlist_ids=self.unique_identifier)


# TODO: Validate
class PlaylistItems(EndpointFile[PlaylistItemsModel]):
    """Playlist items file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> PlaylistItemsEndpoint:
        return not_yt_dlapi().playlist_items

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
            return self._endpoint().download_merged(self.unique_identifier)

        pages: list[str] = []
        page_token: str | None = None
        reached_existing_video = False
        downloaded_all_pages = False
        while not (reached_existing_video or downloaded_all_pages):
            downloaded_page = self._endpoint().download(
                self.unique_identifier,
                page_token=page_token,
            )
            pages.append(downloaded_page)
            loaded_page = self._endpoint().load(downloaded_page, self.log_id())
            page_token = loaded_page.next_page_token
            downloaded_all_pages = page_token is None

            reached_existing_video = any(
                item.snippet.published_at < self.database_record.data_timestamp
                for item in loaded_page.items
            )

        if downloaded_all_pages:
            return self._endpoint().merge_pages(pages)
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
    # TODO: Validate
    @override
    def _endpoint(self) -> VideosEndpoint:
        return not_yt_dlapi().videos


# TODO: Validate
class MusicPlaylist(EndpointFile[MusicModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> MusicEndpoint:
        return not_yt_dlapi().music

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
class TopicReleases(PagedEndpointFile[TopicModel]):
    """The albums and singles a musician's Topic channel lists.

    The channel lists a dozen releases on a shelf and the rest behind it, and a
    shelf release is listed again by the first page behind it, so the pages are
    stored as they were served and read back as one listing with each release
    named once.
    """

    # TODO: Validate
    @override
    def _endpoint(self) -> TopicEndpoint:
        return not_yt_dlapi().topic

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

    # TODO: Validate
    @override
    def _endpoint(self) -> ShowsEndpoint:
        return not_yt_dlapi().shows

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
    def _endpoint(self) -> LoadEndpoint[ChannelFeedModel | PlaylistFeedModel]:
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
                    "PlaylistFeed fetch for {} returned HTTP {}.",
                    self.unique_identifier,
                    error.status_code,
                )
                raise
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
    def _url(self) -> str:
        return f"https://www.youtube.com/show/{self.show_key}"

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            response = get_around_client().get(self._url())
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
