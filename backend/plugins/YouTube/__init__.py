# TODO: Validate

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, override

from loguru import logger
from not_yt_dlapi.exceptions import (
    ChannelFeedNotFoundError,
    PlaylistFeedNotFoundError,
)

from app.channels.models import URLStatus
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.YouTube.importer import YouTubeImporter
from plugins.YouTube.music_importer import YouTubeMusicImporter
from plugins.YouTube.shared import YouTubeShared
from plugins.YouTube.url_parser import YouTubeURLParserMixin
from plugins.YouTube.utils import (
    is_quota_error,
)

if TYPE_CHECKING:
    from app.channels.models import ChannelQueue
    from app.titles.models import Title


# TODO: Validate
class YouTube(
    YouTubeURLParserMixin,
    YouTubeShared,
    AbstractPlugin,
    register=True,
):
    # TODO: Validate
    @classmethod
    @override
    def specialized_updater(cls) -> bool:
        return True

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> YouTubeImporter:
        if title.media_type == MediaType.youtube_artist:
            return YouTubeMusicImporter(self.session, self.plugin, self._file_cache)
        return self.media_importer_from_title_key(title.key)

    # TODO: Validate
    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        if isinstance(error, ChannelFeedNotFoundError | PlaylistFeedNotFoundError):
            season.update_at = tz_datetime.now() + timedelta(hours=1)
            return
        if is_quota_error(error):
            season.update_at = tz_datetime.now() + timedelta(hours=24)
            return
        super().on_update_season_failure(season, error)

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
