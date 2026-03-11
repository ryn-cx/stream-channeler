# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, override

from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.video.models import VideoModel
from sqlmodel import Session, col, select
from yt_dlapi import YTDLAPI
from yt_dlapi.channel.models import ChannelModel
from yt_dlapi.channel_playlists.models import ChannelPlaylistsModel
from yt_dlapi.playlist.models import PlaylistModel
from yt_dlapi.playlist_videos.models import Entry as VideoEntry
from yt_dlapi.playlist_videos.models import PlaylistVideosModel

# import-untyped - There are no type stubs, there is nothing you can do about that.
from yt_dlp.utils import DownloadError  # type: ignore[import-untyped]

from app.config import settings
from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.base_plugin import BasePlugin, JSONFile
from app.plugins.plugins.utils.ip_validator import (
    check_ip_matches,
    check_ip_not_matches,
)
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


@cache
def yt_dlapi_client() -> YTDLAPI:
    return YTDLAPI()


@cache
def not_yt_dlapi_client() -> NotYTDLAPI:
    if settings.YOUTUBE_API_KEY == "changethis":
        msg = "YOUTUBE_API_KEY is not set."
        raise ValueError(msg)
    return NotYTDLAPI(settings.YOUTUBE_API_KEY)


class ChannelById(JSONFile[ChannelModel]):
    def __init__(self, db: Session, plugin: Plugin, show_key: str) -> None:
        self.__show_key = show_key
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_key

    @override
    def _download(self) -> None:
        with self._log_download(self.__show_key):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            channel = yt_dlapi_client().channel
            content = None
            try:
                response = channel.get_by_id(self.__show_key)
                content = channel.dump_response(response)
            # Occurs when a user puts in an invalid channel URL.
            except DownloadError as e:
                if str(e) != (
                    f"ERROR: [youtube:tab] {self.__show_key}: "
                    "YouTube said: This channel does not exist."
                ):
                    raise

            self._write(content)

    @override
    def _parse(self, raw: Any) -> ChannelModel:
        return yt_dlapi_client().channel.parse(raw)


class ChannelByName(JSONFile[ChannelModel]):
    def __init__(self, db: Session, plugin: Plugin, channel_name: str) -> None:
        self.__channel_name = channel_name
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__channel_name

    @override
    def _download(self) -> None:
        with self._log_download(self.__channel_name):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            channel = yt_dlapi_client().channel
            content = None
            try:
                response = channel.get_by_name(self.__channel_name)
                content = channel.dump_response(response)
            # Occurs when a user puts in an invalid channel URL.
            except DownloadError as e:
                if str(e) != (
                    f"ERROR: [youtube:tab] @{self.__channel_name}: "
                    "Unable to download API page: "
                    "HTTP Error 404: "
                    "Not Found (caused by <HTTPError 404: Not Found>)"
                ):
                    raise

            self._write(content)

    @override
    def _parse(self, raw: Any) -> ChannelModel:
        return yt_dlapi_client().channel.parse(raw)


class Playlist(JSONFile[PlaylistModel]):
    def __init__(self, db: Session, plugin: Plugin, season_key: str) -> None:
        self.__season_key = season_key
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__season_key

    @override
    def _download(self) -> None:
        with self._log_download(self.__season_key):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            playlist = yt_dlapi_client().playlist
            content = None
            try:
                response = playlist.get(self.__season_key)
                content = playlist.dump_response(response)
            # Occurs when a user puts in an invalid playlist URL.
            except DownloadError as e:
                if str(e) != (
                    f"ERROR: [youtube:tab] {self.__season_key}: "
                    "YouTube said: The playlist does not exist."
                ):
                    raise

            self._write(content)

    @override
    def _parse(self, raw: Any) -> PlaylistModel:
        return yt_dlapi_client().playlist.parse(raw)


class ChannelPlaylists(JSONFile[ChannelPlaylistsModel]):
    def __init__(self, db: Session, plugin: Plugin, show_key: str) -> None:
        self.__show_key = show_key
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_key

    @override
    def _download(self) -> None:
        with self._log_download(self.__show_key):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            channel_playlists = yt_dlapi_client().channel_playlists
            content = None
            try:
                response = channel_playlists.get_by_id(self.__show_key)
                content = channel_playlists.dump_response(response)
            # Occurs when a channel has no playlists.
            except DownloadError as e:
                if str(e) != (
                    f"ERROR: [youtube:tab] {self.__show_key}: "
                    "This channel does not have a playlists tab"
                ):
                    raise

            self._write(content)

    @override
    def _parse(self, raw: Any) -> ChannelPlaylistsModel:
        return yt_dlapi_client().channel_playlists.parse(raw)


class PlaylistVideos(JSONFile[PlaylistVideosModel]):
    def __init__(self, db: Session, plugin: Plugin, season_key: str) -> None:
        self.__season_key = season_key
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__season_key

    @override
    def _download(self) -> None:
        with self._log_download(self.__season_key):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            playlist_videos = yt_dlapi_client().playlist_videos
            content = None
            try:
                response = playlist_videos.get(self.__season_key)
                content = playlist_videos.dump_response(response)
            # Occurs when downloading the uploads playlist for a channel with no videos.
            except DownloadError as e:
                if str(e) != (
                    f"ERROR: [youtube:tab] {self.__season_key}: "
                    "YouTube said: The playlist does not exist."
                ):
                    raise

            self._write(content)

    @override
    def _parse(self, raw: Any) -> PlaylistVideosModel:
        return yt_dlapi_client().playlist_videos.parse(raw)


class Video(JSONFile[VideoModel]):
    def __init__(self, db: Session, plugin: Plugin, episode_key: str) -> None:
        self.__episode_key = episode_key
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__episode_key

    @override
    def _download(self) -> None:
        with self._log_download(self.__episode_key):
            check_ip_matches(settings.YOUTUBE_API_IP)
            # yt-dlapi is unable to get video information when run from a server or
            # vpn, so not-yt-dlapi needs to be used instead to get video information.
            video = not_yt_dlapi_client().video
            response = video.get(self.__episode_key)
            content = video.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> VideoModel:
        return not_yt_dlapi_client().video.parse(raw)


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
        self.__video_sort_order: dict[str, dict[str, int]] = {}
        self.__channel_by_id_cache: dict[str, ChannelById] = {}
        self.__channel_playlists_cache: dict[str, ChannelPlaylists] = {}
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    # region File Wrappers

    def _channel_by_id_file(self, show_key: str) -> ChannelById:
        return self._get_cached_file(
            self.__channel_by_id_cache,
            show_key,
            lambda: ChannelById(self.db, self.plugin, show_key),
        )

    def _channel_by_name_file(self, channel_name: str) -> ChannelByName:
        return ChannelByName(self.db, self.plugin, channel_name)

    def _channel_playlists_file(self, show_key: str) -> ChannelPlaylists:
        return self._get_cached_file(
            self.__channel_playlists_cache,
            show_key,
            lambda: ChannelPlaylists(self.db, self.plugin, show_key),
        )

    def _playlist_file(self, season_key: str) -> Playlist:
        return Playlist(self.db, self.plugin, season_key)

    def _playlist_videos_file(self, season_key: str) -> PlaylistVideos:
        return PlaylistVideos(self.db, self.plugin, season_key)

    def _video_file(self, episode_key: str) -> Video:
        return Video(self.db, self.plugin, episode_key)

    # endregion File Wrappers

    # region File Groups

    @override
    def _show_files(self, show_key: str) -> Sequence[ChannelById | ChannelPlaylists]:
        return [
            # Required to detect changes to the show (channel).
            self._channel_by_id_file(show_key),
            # Required to detect new seasons (playlists).
            self._channel_playlists_file(show_key),
        ]

    @override
    def _season_files(self, season_key: str) -> Sequence[Playlist | PlaylistVideos]:
        return [
            # Required to detect changes to the season (playlist).
            self._playlist_file(season_key),
            # Required to detect new episodes (videos).
            self._playlist_videos_file(season_key),
        ]

    @override
    def _episode_files(self, episode_key: str) -> Sequence[Video]:
        # Required to detect changes to the episode (video).
        return [self._video_file(episode_key)]

    # endregion File Groups

    # region Timestamps

    def _show_timestamp(self, show_key: str) -> datetime:
        return super()._show_timestamp(show_key)

    def _season_timestamp(self, playlist_key: str) -> datetime:
        return super()._season_timestamp(playlist_key)

    def _episode_timestamp(self, episode_key: str) -> datetime:
        return super()._episode_timestamp(episode_key)

    # endregion Timestamps

    # region Preload

    @override
    def _preload_show_files(self, show_key: str) -> Sequence[File]:
        channel_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        ChannelById.file_key(show_key),
                        ChannelPlaylists.file_key(show_key),
                    ],
                ),
            )
        )
        return self.db.exec(channel_file_select).all()

    @override
    def _preload_season_files(self, season_keys: list[str]) -> Sequence[File]:
        file_keys: list[str] = []
        for season_key in season_keys:
            file_keys.append(Playlist.file_key(season_key))
            file_keys.append(PlaylistVideos.file_key(season_key))

        playlist_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(col(File.key).in_(file_keys))
        )
        return self.db.exec(playlist_file_select).all()

    @override
    def _preload_episode_files(self, episode_keys: list[str]) -> Sequence[File]:
        video_keys = [Video.file_key(video_key) for video_key in episode_keys]
        video_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(col(File.key).in_(video_keys))
        )
        return self.db.exec(video_file_select).all()

    # endregion Preload

    def _video_is_valid(self, video: VideoEntry) -> bool:
        """Check if a video is valid for importing.

        This will ignore deleted and private videos.
        """
        # If the channel_id is None the video is deleted or private
        return video.channel_id is not None

    def _get_channel_uploads_playlist_key(self, show_key: str) -> str:
        """Returns the playlist ID for the channel's uploads."""
        return show_key[:1] + "U" + show_key[2:]

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        season_keys: list[str] = []

        season_keys.append(self._get_channel_uploads_playlist_key(show_key))

        channel_playlists_json = self._channel_playlists_file(show_key)
        # Handle channels with no playlists.
        if channel_playlists_json.get_content():
            playlist_entries = channel_playlists_json.parsed().entries
            season_keys.extend(playlist.id for playlist in playlist_entries)

        return season_keys

    @override
    def _video_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        video_keys: list[str] = []
        for season_key in season_keys:
            playlist_videos_file = self._playlist_videos_file(season_key)
            if playlist_videos_file.get_content():
                video_keys.extend(
                    video.id
                    for video in playlist_videos_file.parsed().entries
                    if self._video_is_valid(video)
                )
        return video_keys

    def _video_sort_order(self, season_key: str) -> dict[str, int]:
        """Map video IDs to their sort order in the playlist."""
        if season_key not in self.__video_sort_order:
            result: dict[str, int] = {}
            playlist_videos_file = self._playlist_videos_file(season_key)
            if playlist_videos_file.get_content():
                for i, video in enumerate(
                    reversed(playlist_videos_file.parsed().entries),
                ):
                    if self._video_is_valid(video) and video.id not in result:
                        result[video.id] = i
            # Only cache the most recent value.
            self.__video_sort_order = {season_key: result}
        return self.__video_sort_order[season_key]
