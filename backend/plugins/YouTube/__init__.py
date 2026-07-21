"""YouTube plugin."""

# TODO: Validate
import re
from datetime import timedelta
from typing import Any, ClassVar, override

from loguru import logger
from not_yt_dlapi.channel.models import Item as ChannelItem
from not_yt_dlapi.playlists.models import Item as PlaylistsItem
from pydantic import TypeAdapter

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.YouTube.files import FileMixin, get_first_item
from plugins.YouTube.handlers import (
    ChannelHandleURLHandler,
    ChannelKeyURLHandler,
    ChannelUsernameURLHandler,
    PlaylistURLHandler,
    PlaylistVideoURLHandler,
    VideoURLHandler,
    YouTubeURLHandler,
)
from plugins.YouTube.watch_history import WatchHistoryMixin


class YouTube(WatchHistoryMixin, FileMixin, register=True):
    """YouTube plugin."""

    _VERSION = "0.0.1"

    # _playlist_video before _video and _username before _handle due to regex overlap.
    _URL_HANDLERS: ClassVar[tuple[type[YouTubeURLHandler], ...]] = (
        PlaylistVideoURLHandler,
        PlaylistURLHandler,
        VideoURLHandler,
        ChannelKeyURLHandler,
        ChannelUsernameURLHandler,
        ChannelHandleURLHandler,
    )

    @classmethod
    def __long_domain(cls) -> str:
        return "youtube.com"

    @classmethod
    def __short_domain(cls) -> str:
        return "youtu.be"

    @classmethod
    @override
    def domains(cls) -> list[str]:
        return [cls.__long_domain(), cls.__short_domain()]

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Channel]\n"
            "> `https://www.youtube.com/@jawed`\n"
            "> `https://www.youtube.com/jawed`\n"
            "> `https://www.youtube.com/c/jawed`\n"
            "> `https://www.youtube.com/user/jawed`\n"
            "> `https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A`\n"
            "> [!TIP/Playlist]\n"
            "> `https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh`\n"
            "> [!TIP/Video]\n"
            "> `https://www.youtube.com/watch?v=jNQXAC9IVRw`\n"
            "> `https://youtu.be/jNQXAC9IVRw`\n"
            "> `https://www.youtube.com/shorts/jNQXAC9IVRw`\n"
            "> [!TIP/Video in Playlist]\n"
            "> `https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh`\n"
            "> `https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh`"
        )

    @classmethod
    @override
    def _url_regex(cls) -> str:
        long_domain_regex = cls._regex_escape_domain(cls.__long_domain())
        short_domain_regex = cls._regex_escape_domain(cls.__short_domain())
        alternatives = "|".join(
            # Strip named groups to non-capturing so handlers that share a group name
            # (e.g. playlist_key) do not collide when the alternatives are combined.
            re.sub(
                r"\(\?P<[^>]+>",
                "(?:",
                handler_class.full_regex(long_domain_regex, short_domain_regex),
            )
            for handler_class in cls._URL_HANDLERS
        )
        return f"(?:{alternatives})"

    def _get_url_handler(self, url: str) -> YouTubeURLHandler:
        long_domain_regex = self._regex_escape_domain(self.__long_domain())
        short_domain_regex = self._regex_escape_domain(self.__short_domain())
        for handler_class in self._URL_HANDLERS:
            regex = handler_class.full_regex(long_domain_regex, short_domain_regex)
            if match := re.match(regex, url):
                return handler_class(self, url, match)

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        handler = self._get_url_handler(url)
        handler.validate_url()
        show = self._import_show(handler.show_key, handler.playlist_key)
        return handler.import_results(show)

    def _import_show(self, show_key: str, playlist_key: str) -> Show:
        show = self._preload_show(show_key, preload_episodes=True).one_or_none()
        if not show:
            _cache = self._download_show_files_and_children(show_key)
            return self._upsert_show(self.source, show_key)

        if self._playlist_is_missing(show, playlist_key):
            _cache = self._download_show_files_and_children(show, tz_datetime.now())
            return self._upsert_show(self.source, show_key)

        return show

    def _playlist_is_missing(self, show: Show, playlist_key: str) -> bool:
        # If the playlist being checked is the channel uploads playlist it should only
        # be considered missing if the channel has at least one upload.
        if playlist_key == self.channel_uploads_playlist_key(show.key):
            channel_by_channel_id = self.channel_by_channel_id_file(show.key)
            channel_item = get_first_item(channel_by_channel_id.parsed().items)
            if int(channel_item.statistics.video_count) == 0:
                return False
        return not Season.get_from_memory(self.session, show, playlist_key)

    @classmethod
    def _playlist_url(cls, playlist_key: str) -> str:
        return cls.build_url(f"playlist?list={playlist_key}")

    @staticmethod
    def _best_thumbnail_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
        # It sounds wrong but standard is a higher resolution than high.
        for quality in ("maxres", "standard", "high", "medium", "default"):
            if thumb := getattr(thumbnails, quality, None):
                return thumb.url
        return None

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url="https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png",
            data_timestamp=self._existing_data_timestamp_or_now(source),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if show_check := self._show_check(source, show_key, force=force):
            channel_file = self.channel_by_channel_id_file(show_key)
            channel_item = get_first_item(channel_file.parsed().items)
            show_files = self._show_files(show_key)
            show = Show(
                key=channel_item.id,
                name=channel_item.snippet.title,
                url=self.build_url(f"channel/{channel_item.id}"),
                media_type="YouTube Channel",
                # Updating every 30 days is reasonable because this is only used for
                # checking for new playlists and changes to the channel information.
                update_at=channel_file.data_timestamp + timedelta(days=30),
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
                image_url=self._best_thumbnail_url(channel_item.snippet.thumbnails),
            ).upsert_and_set_update_at(source, show_check.record, show_files)
        else:
            show = show_check.record

        self._upsert_seasons(show, show_key, force=force)
        return show

    def _upsert_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        self._upsert_channel_uploads_season(show, show_key, force=force)
        self._upsert_playlist_seasons(show, show_key, force=force)
        self._upsert_album_seasons(show, show_key, force=force)
        self.soft_delete_missing_seasons(show_key)

    def _upsert_season(  # noqa: PLR0913
        self,
        show: Show,
        show_key: str,
        season_key: str,
        name: str,
        playlist: ChannelItem | PlaylistsItem,
        *,
        force: bool = False,
    ) -> None:
        if season_check := self._season_check(show, season_key, show_key, force=force):
            season_files = self._season_files(season_key, show_key)
            season = Season(
                key=season_key,
                name=name,
                url=self._playlist_url(season_key),
                image_url=self._best_thumbnail_url(playlist.snippet.thumbnails),
                data_timestamp=season_check.data_timestamp,
                update_at=season_check.data_timestamp + timedelta(hours=1),
                show_id=show.id,
            ).upsert_and_set_update_at(show, season_check.record, season_files)
        else:
            season = season_check.record
        self._upsert_episodes(season, show_key, force=force)

    def _upsert_channel_uploads_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        channel_item = get_first_item(
            self.channel_by_channel_id_file(show_key).parsed().items,
        )
        if int(channel_item.statistics.video_count) == 0:
            return
        uploads_key = self.channel_uploads_playlist_key(show.key)
        self._upsert_season(
            show=show,
            show_key=show_key,
            season_key=uploads_key,
            name=f"Uploads from {show.name}",
            playlist=channel_item,
            force=force,
        )

    def _upsert_album_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for season_key in self._album_season_keys(show_key):
            playlist = get_first_item(
                self.playlist_info_file(season_key).parsed().items,
            )
            self._upsert_season(
                show=show,
                show_key=show_key,
                season_key=season_key,
                name=playlist.snippet.title,
                playlist=playlist,
                force=force,
            )

    def _upsert_playlist_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        channel_playlists_file = self.channel_playlists_file(show_key)
        if not channel_playlists_file.database_record.content:
            return
        playlists_by_key = {
            parsed_playlist.id: parsed_playlist
            for parsed_playlist in channel_playlists_file.parsed().items
        }
        uploads_key = self.channel_uploads_playlist_key(show.key)
        for season_key in self._season_keys_from_file(show_key):
            if season_key != uploads_key and season_key in playlists_by_key:
                playlist = playlists_by_key[season_key]
                self._upsert_season(
                    show=show,
                    show_key=show_key,
                    season_key=season_key,
                    name=playlist.snippet.title,
                    playlist=playlist,
                    force=force,
                )

    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        seen: set[str] = set()
        for item in self.playlist_items_file(season.key).parsed().items:
            episode_key = item.content_details.video_id
            if not self._video_is_valid(item.snippet.title) or episode_key in seen:
                continue
            seen.add(episode_key)

            episode_check = self._episode_check(
                episode_key,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue

            video_item = self.videos_file(episode_key).parsed().items[0]
            video_snippet = video_item.snippet

            duration = None
            duration_timedelta = video_item.content_details.duration:
            logger.info(
                "String duration for video {}: {!r}",
                video_item.id,
                duration_timedelta,
            )
            duration = int(duration_timedelta.total_seconds())

            episode_files = self._episode_files(episode_key, season.key, show_key)
            Episode(
                key=video_item.id,
                name=video_snippet.title,
                url=self.build_url(f"watch?v={video_item.id}"),
                description=video_snippet.description,
                release_date=video_snippet.published_at,
                air_date=video_snippet.published_at,
                duration=duration,
                image_url=self._best_thumbnail_url(video_snippet.thumbnails),
                sort_order=item.snippet.position,
                episode_identifier=f"Youtube {video_item.id}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert_and_set_update_at(season, episode_check.record, episode_files)
        self.soft_delete_missing_episodes(season.key)

    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(season.id, preload_show=True).one()
        playlist_feed = self.playlist_feed_file(season.key)
        old_video_ids: set[str] = set()
        if not playlist_feed.is_outdated() and playlist_feed.database_record.content:
            old_video_ids = set(playlist_feed.video_ids())
        playlist_feed.download_if_outdated(season.update_at)

        # A failed fetch leaves the stored feed untouched, so it is still outdated.
        if playlist_feed.is_outdated(season.update_at):
            logger.warning(
                "PlaylistFeed for season {} is unavailable, skipping new video check.",
                season.key,
            )
            self._preload_and_upsert_show(season.show)
            season.update_at = tz_datetime.now() + timedelta(hours=1)
            return

        new_video_ids = set(playlist_feed.video_ids()) - old_video_ids
        if new_video_ids:
            logger.info(
                "Found {} new videos in season {}: {}",
                len(new_video_ids),
                season.key,
                ", ".join(sorted(new_video_ids)),
            )
            self._download_season_files_and_children(
                season,
                update_at=tz_datetime.now(),
            )
        self._preload_and_upsert_show(season.show)
        season.update_at = playlist_feed.data_timestamp + timedelta(hours=1)

    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        season.update_at = tz_datetime.now() + timedelta(hours=1)
