# TODO: Validate
"""YouTube plugin."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, override

from loguru import logger

from app.channels.models import URLStatus
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin_v3.base import BaseReadURL
from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer
from plugins.YouTube.media import YouTubeMedia
from plugins.YouTube.shared import YouTubeShared
from plugins.YouTube.utils import is_quota_error

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.channels.models import ChannelQueue
    from app.seasons.models import Season
    from app.shows.models import Show


# TODO: Validate
class YouTubeInitializer(BasePluginInitializer, YouTubeShared): ...


# TODO: Validate
class YouTube(YouTubeShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = YouTubeInitializer

    # TODO: Validate
    @classmethod
    @override
    def specialized_updater(cls) -> bool:
        return True

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return YouTubeMedia._url_regexes()  # noqa: SLF001 - The importer owns the addresses.

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        return YouTubeMedia.url_regex()

    # TODO: Validate
    @override
    def get_media_importer(self, input: Show | str) -> YouTubeMedia:
        return YouTubeMedia(self)

    # TODO: Validate
    def update_seasons(self, seasons: Sequence[Season]) -> None:
        YouTubeMedia(self).update_seasons(seasons)

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
