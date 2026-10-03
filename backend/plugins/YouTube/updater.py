# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, override

from loguru import logger

from app.channels.models import URLStatus
from app.utils import tz_datetime
from plugins.utils.base_plugin.updater import BasePluginUpdater
from plugins.YouTube.constants import LINKS_SOURCE_KEY, MUSIC_SOURCE_KEY
from plugins.YouTube.shared import YouTubeShared

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.channels.models import ChannelQueue


# TODO: Validate
class YouTubeUpdater(YouTubeShared, BasePluginUpdater):
    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return []

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (
            cls.plugin_name(),
            # FREE_SOURCE_KEY,
            # PAID_SOURCE_KEY,
            LINKS_SOURCE_KEY,
            MUSIC_SOURCE_KEY,
        )

    # TODO: Validate
    def download_missing_videos(self, video_keys: Iterable[str]) -> None:
        videos_files = [self.videos_file(video_key) for video_key in video_keys]
        self._preload_files(videos_files)
        self.batch_download_missing_videos(videos_files)

    # TODO: Validate
    def on_import_url_failure(
        self,
        queue_item: ChannelQueue,
        error: Exception,
    ) -> None:
        if not self.is_quota_error(error):
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
