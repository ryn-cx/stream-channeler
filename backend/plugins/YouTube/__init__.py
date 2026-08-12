# TODO: Validate
"""YouTube plugin."""

import re
from datetime import timedelta
from typing import ClassVar, override

from loguru import logger

from app.canonical_media.service import reconcile_show
from app.canonical_shows.models import CanonicalShow
from app.channels.models import ChannelQueue, URLStatus
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.YouTube.files import (
    get_first_item,
    is_quota_error,
    is_show_key,
    is_show_season_key,
    is_video_key,
)
from plugins.YouTube.handlers import (
    ChannelHandleURLHandler,
    ChannelKeyURLHandler,
    ChannelUsernameURLHandler,
    PlaylistURLHandler,
    PlaylistVideoURLHandler,
    ShowURLHandler,
    VideoURLHandler,
    YouTubeURLHandler,
)
from plugins.YouTube.helpers import HelperMixin
from plugins.YouTube.source import SourceMixin
from plugins.YouTube.upsert import UpsertMixin
from plugins.YouTube.watch_history import WatchHistoryMixin

_QUOTA_RETRY_DELAY = timedelta(hours=24)
_VIDEO_SEASON_UPDATE_DELAY = timedelta(days=7)


# TODO: Validate
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

    # _playlist_video before _video, and _username and _show before _handle, due to
    # regex overlap.
    _URL_HANDLERS: ClassVar[tuple[type[YouTubeURLHandler], ...]] = (
        PlaylistVideoURLHandler,
        PlaylistURLHandler,
        VideoURLHandler,
        ChannelKeyURLHandler,
        ShowURLHandler,
        ChannelUsernameURLHandler,
        ChannelHandleURLHandler,
    )

    # TODO: Validate
    @classmethod
    def __long_domain(cls) -> str:
        return "youtube.com"

    # TODO: Validate
    @classmethod
    def __short_domain(cls) -> str:
        return "youtu.be"

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        return [cls.__long_domain(), cls.__short_domain()]

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
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

    # TODO: Validate
    def get_url_handler(self, url: str) -> YouTubeURLHandler:
        long_domain_regex = self._regex_escape_domain(self.__long_domain())
        short_domain_regex = self._regex_escape_domain(self.__short_domain())
        for handler_class in self._URL_HANDLERS:
            regex = handler_class.full_regex(long_domain_regex, short_domain_regex)
            if match := re.match(regex, url):
                return handler_class(self, url, match)

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: CanonicalShow | None = None,
    ) -> list[URLImportResult]:
        self._supplied_canonical_show = canonical_show
        handler = self.get_url_handler(url)
        handler.raise_if_invalid()
        show = self._import_show(handler.show_key, handler.playlist_key)
        return handler.import_results(show)

    # TODO: Validate
    @override
    def on_import_url_failure(
        self,
        queue_item: ChannelQueue,
        error: Exception,
    ) -> None:
        if not is_quota_error(error):
            raise error

        import_at = tz_datetime.now() + _QUOTA_RETRY_DELAY
        logger.warning(
            "YouTube API quota is spent, delaying the import of {} until {}.",
            queue_item.url,
            import_at,
        )
        queue_item.status = URLStatus.PENDING
        queue_item.import_at = import_at
        queue_item.note = "YouTube API quota exceeded, retrying in 24 hours."

    # A YouTube show is always imported for a specific playlist.
    # TODO: Validate
    def _import_show(self, show_key: str, playlist_key: str) -> Show:  # type: ignore[override]
        show_preload = self._preload_show(show_key, preload_episodes=True)
        if not (show := show_preload.one_or_none()):
            _cache = self._download_show_files_and_children(show_key)
            return self._upsert_and_reconcile_show(show_key)

        if self._playlist_is_missing(show, playlist_key):
            _cache = self._download_show_files_and_children(show, tz_datetime.now())
            return self._upsert_and_reconcile_show(show_key)

        return show

    # TODO: Validate
    def _upsert_and_reconcile_show(self, show_key: str) -> Show:
        """Upsert the show and point it at the media it is a copy of.

        What `_import_show` does for every other plugin, kept here because a
        YouTube show is imported for one playlist at a time. Without it a video
        that is in the uploads and in a playlist would be two episodes to watch
        rather than one, and the first update of the show would have to move
        every copy onto the record it was always of.
        """
        show = self.upsert_show(self.source, show_key)
        self._unshare_canonical_episodes(show)
        reconcile_show(self.session, show, self.plugin_key())
        return show

    # TODO: Validate
    def _playlist_is_missing(self, show: Show, playlist_key: str) -> bool:
        # A URL for a whole show asks for every season it has, so nothing is missing
        # as long as it has been imported with seasons.
        if is_show_key(playlist_key) and not is_show_season_key(playlist_key):
            return not show.active_children

        # If the playlist being checked is the channel uploads playlist it should only
        # be considered missing if the channel has at least one upload.
        if playlist_key == self.channel_uploads_playlist_key(show.key):
            channel_by_channel_id = self.channel_by_channel_id_file(show.key)
            channel_item = get_first_item(channel_by_channel_id.parsed().items)
            if int(channel_item.statistics.video_count) == 0:
                return False
        return not Season.get_from_memory(self.session, show, playlist_key)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(season.id, preload_show=True).one()
        # A season that is a single video has no feed to check for new videos.
        # A season that is a single video, or a season of a show, has no feed to
        # check for new videos, so its page is re-read instead.
        if is_video_key(season.key) or is_show_season_key(season.key):
            self._download_season_files_and_children(
                season,
                update_at=season.update_at,
            )
            self._preload_and_upsert_show(season.show)
            season.update_at = tz_datetime.now() + _VIDEO_SEASON_UPDATE_DELAY
            return

        playlist_feed = self.playlist_feed_file(season.key)
        # Without a stored feed there is nothing to compare the download against, so
        # this run only stores the feed and the next one checks it for new videos.
        # Treating every entry as new here would re-download the playlist items that
        # were already downloaded when the season was imported.
        has_stored_feed = bool(
            not playlist_feed.is_outdated() and playlist_feed.database_record.content,
        )
        old_video_ids: set[str] = (
            set(playlist_feed.video_ids()) if has_stored_feed else set()
        )
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

        new_video_ids: set[str] = (
            set(playlist_feed.video_ids()) - old_video_ids if has_stored_feed else set()
        )
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

    # TODO: Validate
    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        season.update_at = tz_datetime.now() + timedelta(hours=1)
