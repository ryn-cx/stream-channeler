# TODO: Validate

from __future__ import annotations

import re
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
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer
from plugins.YouTube.constants import URL_REGEXES
from plugins.YouTube.importer import YouTubeImporter
from plugins.YouTube.music_importer import YouTubeTopicImporter
from plugins.YouTube.shared import YouTubeShared
from plugins.YouTube.url_parser import YouTubeURLParserMixin
from plugins.YouTube.utils import (
    is_quota_error,
)

if TYPE_CHECKING:
    from app.channels.models import ChannelQueue
    from app.titles.models import Title


class YouTubeInitializer(BasePluginInitializer, YouTubeShared): ...


# TODO: Validate
class YouTube(
    YouTubeURLParserMixin,
    YouTubeShared,
    BaseReadURL,
    AbstractPlugin,
    register=False,
):
    initializer = YouTubeInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return URL_REGEXES

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        # Some regex patterns have the same named groups which will cause issues so they
        # are stripped for the simple regex matching check. Also supporting both
        # youtube.com and youtu.be is a mess.
        no_named_groups = "|".join(
            re.sub(r"\(\?P<[^>]+>", "(?:", url_regex)
            for url_regex in cls._url_regexes()
        )
        return f"(?:{no_named_groups})"

    # TODO: Validate
    @override
    def media_importer_from_title(self, title: Title) -> YouTubeImporter:
        if title.media_type == "YouTube Artist":
            return YouTubeTopicImporter(self)
        return self.media_importer_from_title_key(title.key)

    @override
    def update_season(self, season: Season) -> None:
        playlist_feed = self.playlist_feed_file(season.key)

        # PlaylistFeed is not a required file because sometimes it will return 404
        # errors for hours at a time so an initial file may need to be downloaded here.
        if playlist_feed.does_not_exist():
            playlist_feed.download_if_outdated()
            return

        old_feed_video_ids = playlist_feed.video_ids()
        playlist_feed.download_if_outdated(season.update_at)
        season.update_at = playlist_feed.data_timestamp() + timedelta(hours=6)

        if new_video_ids := playlist_feed.video_ids() - old_feed_video_ids:
            logger.info(
                "Found {} new videos in season {}: {}",
                len(new_video_ids),
                season.name or season.key,
                ", ".join(sorted(new_video_ids)),
            )
            super().update_season(season)

    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        if isinstance(error, ChannelFeedNotFoundError | PlaylistFeedNotFoundError):
            season.update_at = tz_datetime.now() + timedelta(hours=1)
            return
        if is_quota_error(error):
            season.update_at = tz_datetime.now() + timedelta(hours=24)
            return
        super().on_update_season_failure(season, error)

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
