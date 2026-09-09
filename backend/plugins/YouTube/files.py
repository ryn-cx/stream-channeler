# TODO: Validate
import json
from abc import ABC
from collections import Counter
from functools import cache
from typing import override

# import re
# from urllib.parse import parse_qs, urlsplit
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

# from not_yt_dlapi.shows import Shows as TitlesEndpoint
# from not_yt_dlapi.shows.models import ShowsModel
from not_yt_dlapi.topic import Topic as TopicEndpoint
from not_yt_dlapi.topic.models import TopicModel
from not_yt_dlapi.videos import Videos as VideosEndpoint
from not_yt_dlapi.videos.models import VideosModel

from app.config import settings
from plugins.utils.base_plugin.files import (
    Endpoint,
    SingleArgEndpointFile,
    MultipleArgEndpointFile,
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
class ChannelFile(MultipleArgEndpointFile[ChannelsModel], ABC):
    # TODO: Validate
    @override
    def _endpoint(self) -> ChannelsEndpoint:
        return not_yt_dlapi().channels

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        # Occurs when importing an invalid channel URL.
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class ChannelByChannelId(ChannelFile):
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # not_yt_dlapi().channels.download does not support positional arguments.
        return self._endpoint().download(channel_id=self.unique_identifier)


# TODO: Validate
class ChannelByHandle(ChannelFile):
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # not_yt_dlapi().channels.download does not support positional arguments.
        return self._endpoint().download(channel_handle=self.unique_identifier)


# TODO: Validate
class ChannelByUsername(ChannelFile):
    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # not_yt_dlapi().channels.download does not support positional arguments.
        return self._endpoint().download(channel_username=self.unique_identifier)


# TODO: Validate
class ChannelPlaylists(MultipleArgEndpointFile[PlaylistsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> PlaylistsEndpoint:
        return not_yt_dlapi().playlists

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download_merged(channel_id=self.unique_identifier)


# # TODO: Validate
# class PlaylistInfo(EndpointFile[PlaylistsModel]):
#     # TODO: Validate
#     @override
#     def _endpoint(self) -> PlaylistsEndpoint:
#         return not_yt_dlapi().playlists

#     # TODO: Validate
#     @override
#     def _download_file(self) -> str:
#         return self._endpoint().download(playlist_ids=self.unique_identifier)


# TODO: Validate
class PlaylistItems(PagedEndpointFile[PlaylistItemsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> PlaylistItemsEndpoint:
        return not_yt_dlapi().playlist_items

    # TODO: Validate
    def items(self) -> list[Item]:
        return [item for page in self.parsed() for item in page.items]

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        record = self._database_record
        if record is None or record.content is None:
            return json.dumps(self._endpoint().download_all(self.unique_identifier))

        stored_pages: list[str] = json.loads(record.content)
        return json.dumps(self._new_pages(stored_pages) + stored_pages)

    # TODO: Validate
    def _new_pages(self, stored_pages: list[str]) -> list[str]:
        stored_video_ids = {
            item["contentDetails"]["videoId"]
            for page in stored_pages
            for item in json.loads(page)["items"]
        }
        pages: list[str] = []
        page_token: str | None = None
        while True:
            downloaded_page = self._endpoint().download(
                self.unique_identifier,
                page_token=page_token,
            )
            pages.append(downloaded_page)
            loaded_page = self._endpoint().load(downloaded_page, self.log_id())
            page_token = loaded_page.next_page_token

            if page_token is None or any(
                item.content_details.video_id in stored_video_ids
                for item in loaded_page.items
            ):
                return pages


# TODO: Validate
class Videos(SingleArgEndpointFile[VideosModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> VideosEndpoint:
        return not_yt_dlapi().videos


# TODO: Validate
class MusicPlaylist(SingleArgEndpointFile[MusicModel]):
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
class Topic(PagedEndpointFile[TopicModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> TopicEndpoint:
        return not_yt_dlapi().topic

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


# # TODO: Update not-ytdlapi's name for this endpoint
# # TODO: Validate
# class Browse(PagedEndpointFile[ShowsModel]):
#     """A TV show on YouTube."""

#     # TODO: Validate
#     @override
#     def _endpoint(self) -> TitlesEndpoint:
#         return not_yt_dlapi().shows

#     # TODO: Validate
#     def title_key(self) -> str | None:
#         match = re.search(r"SC[A-Za-z0-9_-]{20,}", self.record_content or "")
#         return match.group(0) if match else None

#     # TODO: Validate
#     def title_name(self) -> str | None:
#         return next(
#             (
#                 item.playlist_sidebar_primary_info_renderer.title.simple_text
#                 for page in self.parsed()
#                 for item in page.sidebar.playlist_sidebar_renderer.items
#             ),
#             None,
#         )

#     # TODO: Validate
#     def offer_labels(self) -> set[str]:
#         return {
#             badge.metadata_badge_renderer.label
#             for page in self.parsed()
#             for item in page.sidebar.playlist_sidebar_renderer.items
#             for badge in item.playlist_sidebar_primary_info_renderer.badges
#             if badge.metadata_badge_renderer.style == "BADGE_STYLE_TYPE_YPC"
#         }

#     # TODO: Validate
#     def season_numbers(self) -> list[int]:
#         return sorted(self.episode_keys_by_season())

#     # A season is chosen from the same menu a playlist is sorted from, so what tells
#     # the two apart is that a season says which season it is, and it says so in the
#     # address a person would read it at rather than in the endpoint browse is asked
#     # by.
#     # TODO: Validate
#     def _open_season(self, page: ShowsModel) -> int | None:
#         for tab in page.contents.two_column_browse_results_renderer.tabs:
#             for section in tab.tab_renderer.content.section_list_renderer.contents:
#                 for item in section.item_section_renderer.contents:
#                     metadata = item.playlist_show_metadata_renderer
#                     if metadata is None:
#                         continue
#                     for menu_item in (
#                         metadata.collection.sort_filter_sub_menu_renderer.sub_menu_items
#                     ):
#                         if not menu_item.selected:
#                             continue
#                         query = urlsplit(
#                             menu_item.navigation_endpoint.command_metadata.web_command_metadata.url,
#                         ).query
#                         numbers = parse_qs(query).get("season", ())
#                         if numbers and numbers[0].isdigit():
#                             return int(numbers[0])
#         return None

#     # TODO: Validate
#     def _page_episode_keys(self, page: ShowsModel) -> list[str]:
#         return [
#             content.playlist_video_renderer.video_id
#             for tab in page.contents.two_column_browse_results_renderer.tabs
#             for section in tab.tab_renderer.content.section_list_renderer.contents
#             for item in section.item_section_renderer.contents
#             if item.playlist_video_list_renderer is not None
#             for content in item.playlist_video_list_renderer.contents
#         ]

#     # TODO: Validate
#     def episode_keys_by_season(self) -> dict[int, list[str]]:
#         episode_keys: dict[int, list[str]] = {}
#         season_number: int | None = None
#         for page in self.parsed():
#             open_season = self._open_season(page)
#             if open_season is not None:
#                 season_number = open_season
#             if season_number is None:
#                 continue
#             episode_keys.setdefault(season_number, []).extend(
#                 self._page_episode_keys(page),
#             )
#         return episode_keys


# TODO: Validate
class PlaylistFeed(MultipleArgEndpointFile[ChannelFeedModel | PlaylistFeedModel]):
    # TODO: Validate
    def _is_channel_feed(self) -> bool:
        return self.unique_identifier.startswith("UU")

    # TODO: Validate
    @override
    def _endpoint(self) -> Endpoint[ChannelFeedModel | PlaylistFeedModel]:
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
            channel_id = "UC" + self.unique_identifier[2:]
            return not_yt_dlapi().channel_feed.download(channel_id)
        return not_yt_dlapi().playlist_feed.download(self.unique_identifier)

    # TODO: Validate
    # Failed downloads need to be delayed for PlaylistFeed instead of writing the empty
    # file so download_and_write must be overriden.
    @override
    def _download_and_write(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                feed = self._download_file()
            # Playlist feeds are really unreliable and sometimes return 404 errors for
            # no reason.
            except (ChannelFeedNotFoundError, PlaylistFeedNotFoundError) as error:
                logger.warning(
                    "PlaylistFeed fetch for {} returned HTTP {}.",
                    self.unique_identifier,
                    error.status_code,
                )
                raise
            self.write(feed)

    # TODO: Validate
    def video_ids(self) -> set[str]:
        return {entry.video_id for entry in self.parsed().entry}
