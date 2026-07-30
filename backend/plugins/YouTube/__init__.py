# TODO: Validate
"""YouTube plugin."""

import re
from datetime import timedelta
from typing import ClassVar, override

from loguru import logger

from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.YouTube.files import get_first_item
from plugins.YouTube.handlers import (
    ChannelHandleURLHandler,
    ChannelKeyURLHandler,
    ChannelUsernameURLHandler,
    PlaylistURLHandler,
    PlaylistVideoURLHandler,
    VideoURLHandler,
    YouTubeURLHandler,
)
from plugins.YouTube.helpers import HelperMixin
from plugins.YouTube.source import SourceMixin
from plugins.YouTube.upsert import UpsertMixin
from plugins.YouTube.watch_history import WatchHistoryMixin


class YouTube(
    SourceMixin,
    UpsertMixin,
    WatchHistoryMixin,
    HelperMixin,
    register=True,
):
    """YouTube plugin."""

    _VERSION = "0.0.1"

    # TODO: Don't hardcode the favicon URL
    FAVICON_URL = (
        "https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png"
    )

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
