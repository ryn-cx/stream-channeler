# TODO: Validate
"""YouTube plugin."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from loguru import logger

from app.channels.models import ChannelQueue, URLStatus
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.YouTube.base import YouTubeBase
from plugins.YouTube.initialize import YouTubeInitializer
from plugins.YouTube.utils import is_quota_error
from plugins.YouTube.importer import YouTubeImporter


# TODO: Validate
class YouTube(YouTubeBase, AbstractPlugin, register=True):
    """YouTube plugin."""

    initializer = YouTubeInitializer
    importer = YouTubeImporter

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
