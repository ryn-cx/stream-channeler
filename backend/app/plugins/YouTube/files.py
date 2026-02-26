# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache, cached_property
from typing import Any, override

from loguru import logger
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
from app.media.models import Episode, File, Plugin, Season, Show, Source
from app.plugins.utils.base_files import JSONFile
from app.plugins.utils.base_plugin import BasePlugin
from app.plugins.utils.ip_validator import check_ip_matches, check_ip_not_matches


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
    def __init__(self, db: Session, plugin: Plugin, show_id: str) -> None:
        self.__show_id = show_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_id

    @override
    def _download(self) -> None:
        with self._log_download(self.__show_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            channel = yt_dlapi_client().channel
            try:
                response = channel.get_by_id(self.__show_id)
                content = channel.dump_response(response)
                self._write(content)
            # Occurs when a user puts in an invalid channel URL.
            except DownloadError as e:
                if str(e) != (
                    "ERROR: "
                    f"[youtube:tab] {self.__show_id}: YouTube said: "
                    "This channel does not exist."
                ):
                    raise

                self._write("")

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
            try:
                response = channel.get_by_name(self.__channel_name)
                content = channel.dump_response(response)
                self._write(content)
            # Occurs when a user puts in an invalid channel URL.
            except DownloadError as e:
                if str(e) != (
                    "ERROR: "
                    f"[youtube:tab] @{self.__channel_name}: "
                    "Unable to download API page: "
                    "HTTP Error 404: "
                    "Not Found (caused by <HTTPError 404: Not Found>)"
                ):
                    raise

                self._write("")

    @override
    def _parse(self, raw: Any) -> ChannelModel:
        return yt_dlapi_client().channel.parse(raw)


class ChannelPlaylists(JSONFile[ChannelPlaylistsModel]):
    def __init__(self, db: Session, plugin: Plugin, show_id: str) -> None:
        self.__show_id = show_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_id

    @override
    def _download(self) -> None:
        with self._log_download(self.__show_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            channel_playlists = yt_dlapi_client().channel_playlists
            try:
                response = channel_playlists.get_by_id(self.__show_id)
                content = channel_playlists.dump_response(response)
                self._write(content)
            # Occurs when a channel has no playlists.
            except DownloadError as e:
                # TODO: Change this to an exact match
                if "does not have a playlists tab" not in str(e):
                    raise

                self._write("")

    @override
    def _parse(self, raw: Any) -> ChannelPlaylistsModel:
        return yt_dlapi_client().channel_playlists.parse(raw)


class Playlist(JSONFile[PlaylistModel]):
    def __init__(self, db: Session, plugin: Plugin, season_id: str) -> None:
        self.__season_id = season_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__season_id

    @override
    def _download(self) -> None:
        with self._log_download(self.__season_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            playlist = yt_dlapi_client().playlist
            try:
                response = playlist.get(self.__season_id)
                content = playlist.dump_response(response)
                self._write(content)
            # Occurs when a user puts in an invalid playlist URL.
            except DownloadError as e:
                if str(e) != (
                    f"ERROR: [youtube:tab] {self.__season_id}: "
                    "YouTube said: The playlist does not exist."
                ):
                    raise

                self._write("")

    @override
    def _parse(self, raw: Any) -> PlaylistModel:
        return yt_dlapi_client().playlist.parse(raw)


class PlaylistVideos(JSONFile[PlaylistVideosModel]):
    def __init__(self, db: Session, plugin: Plugin, season_id: str) -> None:
        self.__season_id = season_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__season_id

    @override
    def _download(self) -> None:
        with self._log_download(self.__season_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            playlist_videos = yt_dlapi_client().playlist_videos
            response = playlist_videos.get(self.__season_id)
            content = playlist_videos.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> PlaylistVideosModel:
        return yt_dlapi_client().playlist_videos.parse(raw)


class Video(JSONFile[VideoModel]):
    def __init__(self, db: Session, plugin: Plugin, episode_id: str) -> None:
        self.__episode_id = episode_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__episode_id

    @override
    def _download(self) -> None:
        with self._log_download(self.__episode_id):
            check_ip_matches(settings.YOUTUBE_API_IP)
            # yt-dlapi is unable to get video information when run from a server or
            # vpn, so not-yt-dlapi needs to be used instead to get video information.
            video = not_yt_dlapi_client().video
            response = video.get(self.__episode_id)
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
        self.__channel_by_id_file: dict[str, ChannelById] = {}
        self.__channel_by_name_file: dict[str, ChannelByName] = {}
        self.__channel_playlists_file: dict[str, ChannelPlaylists] = {}
        self.__playlist_file: dict[str, Playlist] = {}
        self.__playlist_videos_file: dict[str, PlaylistVideos] = {}
        self.__video_file: dict[str, Video] = {}
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    # region File Cache

    def _channel_by_id_file(self, show_id: str) -> ChannelById:
        return self._get_cached_file(
            self.__channel_by_id_file,
            show_id,
            lambda: ChannelById(self.db, self.plugin, show_id),
        )

    def _channel_by_name_file(self, channel_name: str) -> ChannelByName:
        return self._get_cached_file(
            self.__channel_by_name_file,
            channel_name,
            lambda: ChannelByName(self.db, self.plugin, channel_name),
        )

    def _channel_playlists_file(self, show_id: str) -> ChannelPlaylists:
        return self._get_cached_file(
            self.__channel_playlists_file,
            show_id,
            lambda: ChannelPlaylists(self.db, self.plugin, show_id),
        )

    def _playlist_file(self, season_id: str) -> Playlist:
        return self._get_cached_file(
            self.__playlist_file,
            season_id,
            lambda: Playlist(self.db, self.plugin, season_id),
        )

    def _playlist_videos_file(self, season_id: str) -> PlaylistVideos:
        return self._get_cached_file(
            self.__playlist_videos_file,
            season_id,
            lambda: PlaylistVideos(self.db, self.plugin, season_id),
        )

    def _video_file(self, episode_id: str) -> Video:
        return self._get_cached_file(
            self.__video_file,
            episode_id,
            lambda: Video(self.db, self.plugin, episode_id),
        )

    # endregion File Cache

    # region File Groups

    @override
    def _show_files(self, show_id: str) -> Sequence[ChannelById | ChannelPlaylists]:
        return [
            # Required to detect changes to the show (channel).
            self._channel_by_id_file(show_id),
            # Required to detect new seasons (playlists).
            self._channel_playlists_file(show_id),
        ]

    @override
    def _season_files(self, season_id: str) -> Sequence[Playlist | PlaylistVideos]:
        return [
            # Required to detect changes to the season (playlist).
            self._playlist_file(season_id),
            # Required to detect new episodes (videos).
            self._playlist_videos_file(season_id),
        ]

    @override
    def _episode_files(self, episode_id: str) -> Sequence[Video]:
        # Required to detect changes to the episode (video).
        return [self._video_file(episode_id)]

    # endregion File Groups

    # region Timestamps

    def _show_timestamp(self, show_id: str) -> datetime:
        return super()._show_timestamp(show_id)

    def _season_timestamp(self, playlist_id: str) -> datetime:
        return super()._season_timestamp(playlist_id)

    def _episode_timestamp(self, episode_id: str) -> datetime:
        return super()._episode_timestamp(episode_id)

    # endregion Timestamps

    # region Cached File Values

    @cached_property
    def _season_ids_from_file(self) -> list[str]:
        season_ids: list[str] = []

        # Some channels have playlists but no uploads. yt_dlapi will return an error and
        # a blank file if you try to download the channel uploads playlist for these
        # channels. The channel uploads playlist cannot be imported without this file,
        # so the channel uploads playlist should only be added if there is at least one
        # video that has been uploaded.
        parsed_channel = self._channel_by_id_file(self._show_id).parsed()
        if parsed_channel.entries:
            season_ids.append(self._get_channel_uploads_playlist_id)

        # Some channels have uploads but no playlist. yt_dlapi will return an error and
        # a blank file if you try to download the playlists. If the file is empty it
        # cannot be parsed.
        channel_playlists_json = self._channel_playlists_file(self._show_id)
        if channel_playlists_json.has_file_content():
            playlist_entries = channel_playlists_json.parsed().entries
            season_ids.extend(playlist.id for playlist in playlist_entries)

        return season_ids

    @cached_property
    def _episode_ids_from_file(self) -> list[str]:
        return [
            video.id
            for playlist_id in self._season_ids_from_file
            for video in self._playlist_videos_file(playlist_id).parsed().entries
            if self._video_is_valid(video)
        ]

    # endregion Cached Values

    # region Download

    def _download_initial_files(self) -> None:
        logger.info(f"Downloading All Files For: {self._pretty_show_name()}")
        self.__download_initial_channel_by_id()
        self.__download_initial_channel_playlists()
        self.__download_initial_playlists()
        self.__download_initial_playlist_videos()
        self.__download_initial_videos()

    def __download_initial_channel_by_id(self) -> None:
        self._channel_by_id_file(self._show_id)

    def __download_initial_channel_playlists(self) -> None:
        self._channel_playlists_file(self._show_id)

    def __download_initial_playlists(self) -> None:
        for season_id in self._season_ids_from_file:
            self._playlist_file(season_id)

    def __download_initial_playlist_videos(self) -> None:
        for season_id in self._season_ids_from_file:
            self._playlist_videos_file(season_id)

    def __download_initial_videos(self) -> None:
        for episode_id in self._episode_ids_from_file:
            self._video_file(episode_id)

    # endregion Download

    # region Preload

    def _preload_show_season_episode_files(self) -> None:
        """Preload all of the files for a show, its seasons, and its episodes."""
        self.__preload_channel_files()
        self.__preload_playlist_files()
        self.__preload_video_files()

    def __preload_channel_files(self) -> None:
        channel_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        ChannelById.file_key(self._show_id),
                        ChannelPlaylists.file_key(self._show_id),
                    ],
                ),
            )
        )
        self._add_all_to_preload_cache(channel_file_select)

    def __preload_playlist_files(self) -> None:
        if not (season_ids := self._season_ids_from_file):
            return

        season_keys: list[str] = []
        for season_id in season_ids:
            season_keys.append(Playlist.file_key(season_id))
            season_keys.append(PlaylistVideos.file_key(season_id))

        playlist_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(col(File.key).in_(season_keys))
        )
        self._add_all_to_preload_cache(playlist_file_select)

    def __preload_video_files(self) -> None:
        if not (episode_ids := self._episode_ids_from_file):
            return

        video_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [Video.file_key(eid) for eid in episode_ids],
                ),
            )
        )
        self._add_all_to_preload_cache(video_file_select)

    # endregion Preload

    def _video_is_valid(self, video: VideoEntry) -> bool:
        """Check if a video is valid for importing.

        This will ignore deleted and private videos.
        """
        # If the channel_id is None the video is deleted or private
        return video.channel_id is not None

    @cached_property
    def _get_channel_uploads_playlist_id(self) -> str:
        """Returns the playlist ID for the channel's uploads."""
        return self._show_id[:1] + "U" + self._show_id[2:]
