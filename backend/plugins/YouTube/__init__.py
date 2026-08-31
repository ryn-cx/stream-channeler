from datetime import timedelta
from typing import override

from loguru import logger

from app.channels.models import ChannelQueue, URLStatus
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.YouTube.constants import LONG_DOMAIN, SHORT_DOMAIN
from plugins.YouTube.files import (
    is_an_album,
    is_show_season_key,
    is_video_key,
)
from plugins.YouTube.import_url import ImportURLMixin
from plugins.YouTube.source import SourceMixin
from plugins.YouTube.updater import UpdaterMixin
from plugins.YouTube.upsert import UpsertMixin
from plugins.YouTube.utils import is_quota_error
from plugins.YouTube.watch_history import WatchHistoryMixin


class YouTube(
    SourceMixin,
    UpsertMixin,
    WatchHistoryMixin,
    UpdaterMixin,
    ImportURLMixin,
    register=True,
):
    @classmethod
    @override
    def specialized_updater(cls) -> bool:
        return True

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return (
            "https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png"
        )

    @classmethod
    @override
    def domains(cls) -> list[str]:
        return [LONG_DOMAIN, SHORT_DOMAIN]

    # TODO: Validate
    @override
    def on_import_url_failure(
        self,
        queue_item: ChannelQueue,
        error: Exception,
    ) -> None:
        if not is_quota_error(error):
            raise error

        import_at = tz_datetime.now() + timedelta(hours=24)
        logger.warning(
            "YouTube API quota is spent, delaying the import of {} until {}.",
            queue_item.url,
            import_at,
        )
        queue_item.status = URLStatus.PENDING
        queue_item.import_at = import_at
        queue_item.note = "YouTube API quota exceeded, retrying in 24 hours."

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(season.id, preload_show=True).one()
        # A season that is a single video has no feed to check for new videos.
        # A season that is a single video, or a season of a show, has no feed to
        # check for new videos, so its page is re-read instead.
        if (
            is_video_key(season.key)
            or is_show_season_key(season.key)
            or is_an_album(season.key)
        ):
            self._download_season_files_and_children(
                season,
                update_at=season.update_at,
            )
            self._update_and_upsert_show(season.show)
            season.update_at = tz_datetime.now() + timedelta(days=7)
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
            self._update_and_upsert_show(season.show)
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
        self._update_and_upsert_show(season.show)
        season.update_at = playlist_feed.data_timestamp + timedelta(hours=1)

    # TODO: Validate
    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        season.update_at = tz_datetime.now() + timedelta(hours=1)
