# TODO: Validate
import json
from collections.abc import Sequence
from functools import cache
from typing import override

from loguru import logger
from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.channel import Channels as ChannelsEndpoint
from not_yt_dlapi.channel.models import ChannelModel
from not_yt_dlapi.playlist import Playlists as PlaylistsEndpoint
from not_yt_dlapi.playlist.models import PlaylistModel
from not_yt_dlapi.playlist_item import PlaylistItems as PlaylistItemsEndpoint
from not_yt_dlapi.playlist_item.models import PlaylistItemModel
from not_yt_dlapi.video.models import VideoModel
from sqlmodel import Session

from app.config import settings
from app.episodes.models import Episode
from app.plugins.models import File
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.plugins.plugins.utils.base_plugin.files import (
    GAPIJSON,
    GAPIJSONNoGet,
)
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


@cache
def not_yt_dlapi_client() -> NotYTDLAPI:
    return NotYTDLAPI(settings.YOUTUBE_API_KEY)


class ChannelByChannelId(GAPIJSONNoGet[ChannelModel]):
    api_endpoint = not_yt_dlapi_client().channels

    @override
    def _get(self) -> ChannelModel:
        assert isinstance(self.api_endpoint, ChannelsEndpoint)  # noqa: S101
        return self.api_endpoint.get(channel_id=self.unique_identifier)

    @override
    def _get_acceptable_error(self) -> str:
        return f"Channel '{self.unique_identifier}' not found."


class ChannelByHandle(GAPIJSONNoGet[ChannelModel]):
    api_endpoint = not_yt_dlapi_client().channels

    @override
    def _get(self) -> ChannelModel:
        assert isinstance(self.api_endpoint, ChannelsEndpoint)  # noqa: S101
        return self.api_endpoint.get(handle=self.unique_identifier)

    @override
    def _get_acceptable_error(self) -> str:
        return f"Channel '{self.unique_identifier}' not found."


class ChannelPlaylists(GAPIJSONNoGet[PlaylistModel]):
    api_endpoint = not_yt_dlapi_client().playlists

    @override
    def _get(self) -> PlaylistModel:
        assert isinstance(self.api_endpoint, PlaylistsEndpoint)  # noqa: S101
        return self.api_endpoint.get_all(self.unique_identifier)

    @override
    def _get_acceptable_error(self) -> str:
        return f"No playlists found for channel '{self.unique_identifier}'."


class PlaylistItems(GAPIJSONNoGet[PlaylistItemModel]):
    api_endpoint = not_yt_dlapi_client().playlist_items

    @override
    def _get(self) -> PlaylistItemModel:
        assert isinstance(self.api_endpoint, PlaylistItemsEndpoint)  # noqa: S101
        return self.api_endpoint.get_all(self.unique_identifier)

    @override
    def _get_acceptable_error(self) -> str:
        return "The playlist identified with the request's <code>playlistId</code> parameter cannot be found."


class Videos(GAPIJSON[VideoModel]):
    api_endpoint = not_yt_dlapi_client().videos


class FileMixin(BasePlugin, register=False):
    @override
    def __init__(
        self,
        db: Session,
        *,
        url: str | None = None,
        source: Source | None = None,
        show: Show | None = None,
        season: Season | None = None,
        episode: Episode | None = None,
    ) -> None:
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    # region File Wrappers

    def _channel_by_channel_id_file(self, show_key: str) -> ChannelByChannelId:
        return self._get_weakref_cached_file(
            ChannelByChannelId,
            show_key,
            lambda: ChannelByChannelId(self.db, self.plugin, show_key),
        )

    def _channel_by_handle_file(self, channel_name: str) -> ChannelByHandle:
        return self._get_weakref_cached_file(
            ChannelByHandle,
            channel_name,
            lambda: ChannelByHandle(self.db, self.plugin, channel_name),
        )

    def _channel_playlists_file(self, show_key: str) -> ChannelPlaylists:
        return self._get_weakref_cached_file(
            ChannelPlaylists,
            show_key,
            lambda: ChannelPlaylists(self.db, self.plugin, show_key),
        )

    def _playlist_items_file(self, season_key: str) -> PlaylistItems:
        return self._get_weakref_cached_file(
            PlaylistItems,
            season_key,
            lambda: PlaylistItems(self.db, self.plugin, season_key),
        )

    def _videos_file(self, episode_key: str) -> Videos:
        return self._get_weakref_cached_file(
            Videos,
            episode_key,
            lambda: Videos(self.db, self.plugin, episode_key),
        )

    # endregion File Wrappers

    # region File Groups

    @override
    def _show_files(
        self,
        show_key: str,
    ) -> Sequence[ChannelByChannelId | ChannelPlaylists]:
        return [
            # Required to detect new seasons (playlists).
            self._channel_playlists_file(show_key),
            # ChannelByHandle is only used to get ChannelByChannelId so it is not used.
            # Required to detect changes to the show (channel).
            self._channel_by_channel_id_file(show_key),
        ]

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[ChannelPlaylists | PlaylistItems]:
        return [
            # Required to detect new episodes (videos).
            self._playlist_items_file(season_key),
            # Required to detect changes to the season (playlist).
            self._channel_playlists_file(show_key),
        ]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[Videos]:
        # Required to detect changes to the episode (video).
        return [self._videos_file(episode_key)]

    # endregion File Groups

    def _video_is_valid(self, video_title: str) -> bool:
        """Check if a video is valid for importing."""
        return video_title not in ("Deleted video", "Private video")

    def _get_channel_uploads_playlist_key(self, show_key: str) -> str:
        """Return the playlist ID for the channel's uploads."""
        return show_key[:1] + "U" + show_key[2:]

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        channel_playlists_file = self._channel_playlists_file(show_key)
        season_keys: list[str] = []
        if channel_playlists_file.database_record.content:
            season_keys = [
                item.id
                for item in channel_playlists_file.parsed().items
                if item.content_details.item_count > 0
            ]

        # If the channel has uploads also include that as a season.
        channel_item = self._channel_by_channel_id_file(show_key).parsed().items[0]
        if int(channel_item.statistics.video_count) > 0:
            season_keys.append(self._get_channel_uploads_playlist_key(show_key))

        return season_keys

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        seen: set[str] = set()
        video_keys: list[str] = []
        for season_key in season_keys:
            playlist_items_file = self._playlist_items_file(season_key)
            for item in playlist_items_file.parsed().items:
                video_id = item.content_details.video_id
                if self._video_is_valid(item.snippet.title) and video_id not in seen:
                    seen.add(video_id)
                    video_keys.append(video_id)
        return video_keys

    @override
    def _download_all_episode_files(
        self,
        season_key: str,
        show_key: str,
        preloaded_episodes_files: Sequence[File] | None = None,
    ) -> list[File]:
        """Batch download all videos for a season in a single API call."""
        video_keys = self._episode_keys_from_file(season_key)
        if not preloaded_episodes_files:
            preloaded_episodes_files = self._preload_episode_files(
                video_keys,
                season_key=season_key,
                show_key=show_key,
            )

        outdated_ids = [
            video_id
            for video_id in video_keys
            if self._videos_file(video_id).is_outdated()
        ]

        if outdated_ids:
            logger.info(f"Batch downloading {len(outdated_ids)} videos")
            responses = not_yt_dlapi_client().videos.download_multiple(outdated_ids)
            for video_id, response in zip(outdated_ids, responses, strict=True):
                video_file = self._videos_file(video_id)
                content = json.dumps(response, default=str)
                # This is one of the few places where using _write directly is required
                # because of the way the files are batch downloaded.
                video_file._write(content)  # noqa: SLF001 # type: ignore[reportPrivateUsage]

        return [self._videos_file(video_id).database_record for video_id in video_keys]
