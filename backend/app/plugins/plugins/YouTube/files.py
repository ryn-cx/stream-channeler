from collections.abc import Sequence
from functools import cache
from typing import Any, override

from not_yt_dlapi import NotYTDLAPI
from not_yt_dlapi.video.models import VideoModel
from sqlmodel import Session
from yt_dlapi import YTDLAPI
from yt_dlapi.channel.models import ChannelModel
from yt_dlapi.channel_playlists.models import ChannelPlaylistsModel
from yt_dlapi.playlist.models import PlaylistModel
from yt_dlapi.playlist_videos.models import Entry as VideoEntry
from yt_dlapi.playlist_videos.models import PlaylistVideosModel

from app.config import settings
from app.episodes.models import Episode
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.plugins.plugins.utils.base_plugin.files import GAPIJSON, GAPIJSONNoGet
from app.plugins.plugins.utils.ip_validator import check_ip_matches
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


class ChannelById(GAPIJSONNoGet[ChannelModel]):
    api_endpoint = yt_dlapi_client().channel

    def _get_acceptable_error(self) -> str:
        # Occurs when a user puts in an invalid channel URL.
        return (
            f"ERROR: [youtube:tab] {self.unique_identifier}: "
            "YouTube said: This channel does not exist."
        )

    def _get(self) -> ChannelModel:
        assert isinstance(self.api_endpoint, type(yt_dlapi_client().channel))  # noqa: S101
        return self.api_endpoint.get_by_id(self.unique_identifier)


class ChannelByName(GAPIJSONNoGet[ChannelModel]):
    api_endpoint = yt_dlapi_client().channel

    @override
    def _get_acceptable_error(self) -> str:
        # Occurs when a user puts in an invalid channel URL.
        return (
            f"ERROR: [youtube:tab] @{self.unique_identifier}: "
            "Unable to download API page: "
            "HTTP Error 404: "
            "Not Found (caused by <HTTPError 404: Not Found>)"
        )

    @override
    def _get(self) -> ChannelModel:
        assert isinstance(self.api_endpoint, type(yt_dlapi_client().channel))  # noqa: S101
        return self.api_endpoint.get_by_name(self.unique_identifier)


class Playlist(GAPIJSON[PlaylistModel]):
    api_endpoint = yt_dlapi_client().playlist

    @override
    def _get_acceptable_error(self) -> str:
        # Occurs when a user puts in an invalid playlist URL.
        return (
            f"ERROR: [youtube:tab] {self.unique_identifier}: "
            "YouTube said: The playlist does not exist."
        )


class ChannelPlaylists(GAPIJSONNoGet[ChannelPlaylistsModel]):
    api_endpoint = yt_dlapi_client().channel_playlists

    @override
    def _get_acceptable_error(self) -> str:
        # Occurs when a channel has no playlists.
        return (
            f"ERROR: [youtube:tab] {self.unique_identifier}: "
            "This channel does not have a playlists tab"
        )

    @override
    def _get(self) -> ChannelPlaylistsModel:
        assert isinstance(  # noqa: S101
            self.api_endpoint,
            type(yt_dlapi_client().channel_playlists),
        )
        return self.api_endpoint.get_by_id(self.unique_identifier)


class PlaylistVideos(GAPIJSON[PlaylistVideosModel]):
    api_endpoint = yt_dlapi_client().playlist_videos

    @override
    def _get_acceptable_error(self) -> str:
        # Occurs when downloading the uploads playlist for a channel with no videos.
        return (
            f"ERROR: [youtube:tab] {self.unique_identifier}: "
            "YouTube said: The playlist does not exist."
        )


class Video(GAPIJSON[VideoModel]):
    api_endpoint = not_yt_dlapi_client().video

    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            check_ip_matches(settings.YOUTUBE_API_IP)
            # yt-dlapi is unable to get video information when run from a server or
            # vpn, so not-yt-dlapi needs to be used instead to get video information.
            response = self._get()
            content = self.api_endpoint.dump_response(response)
            self._write(content)


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

    def _channel_by_id_file(self, show_key: str) -> ChannelById:
        return self._get_weakref_cached_file(
            ChannelById,
            show_key,
            lambda: ChannelById(self.db, self.plugin, show_key),
        )

    def _channel_by_name_file(self, channel_name: str) -> ChannelByName:
        return self._get_weakref_cached_file(
            ChannelByName,
            channel_name,
            lambda: ChannelByName(self.db, self.plugin, channel_name),
        )

    def _channel_playlists_file(self, show_key: str) -> ChannelPlaylists:
        return self._get_weakref_cached_file(
            ChannelPlaylists,
            show_key,
            lambda: ChannelPlaylists(self.db, self.plugin, show_key),
        )

    def _playlist_file(self, season_key: str) -> Playlist:
        return self._get_weakref_cached_file(
            Playlist,
            season_key,
            lambda: Playlist(self.db, self.plugin, season_key),
        )

    def _playlist_videos_file(self, season_key: str) -> PlaylistVideos:
        return self._get_weakref_cached_file(
            PlaylistVideos,
            season_key,
            lambda: PlaylistVideos(self.db, self.plugin, season_key),
        )

    def _video_file(self, episode_key: str) -> Video:
        return self._get_weakref_cached_file(
            Video,
            episode_key,
            lambda: Video(self.db, self.plugin, episode_key),
        )

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
    def _season_files(  # type: ignore[override]
        self,
        season_key: str,
        **kwargs: Any,
    ) -> Sequence[Playlist | PlaylistVideos]:
        return [
            # Required to detect changes to the season (playlist).
            self._playlist_file(season_key),
            # Required to detect new episodes (videos).
            self._playlist_videos_file(season_key),
        ]

    @override
    def _episode_files(self, episode_key: str, **kwargs: Any) -> Sequence[Video]:  # type: ignore[override]
        # Required to detect changes to the episode (video).
        return [self._video_file(episode_key)]

    # endregion File Groups

    def _video_is_valid(self, video: VideoEntry) -> bool:
        """Check if a video is valid for importing.

        Ignores deleted and private videos.
        """
        # If the channel_id is None the video is deleted or private
        return video.channel_id is not None

    def _get_channel_uploads_playlist_key(self, show_key: str) -> str:
        """Returns the playlist ID for the channel's uploads."""
        return show_key[:1] + "U" + show_key[2:]

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        season_keys = [self._get_channel_uploads_playlist_key(show_key)]

        channel_playlists_json = self._channel_playlists_file(show_key)
        # Channels with no playlists will have no content which will cause parsed to
        # raise an error.
        if channel_playlists_json.database_entry.content:
            playlist_entries = channel_playlists_json.parsed().entries
            season_keys.extend(playlist.id for playlist in playlist_entries)

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
            playlist_videos_file = self._playlist_videos_file(season_key)
            if playlist_videos_file.database_entry.content:
                for video in playlist_videos_file.parsed().entries:
                    if self._video_is_valid(video) and video.id not in seen:
                        seen.add(video.id)
                        video_keys.append(video.id)
        return video_keys
