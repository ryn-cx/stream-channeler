# TODO: Validate
"""YouTube plugin."""

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
from plugins.YouTube.channel_importer import YouTubeChannelImporter
from plugins.YouTube.constants import URL_REGEXES
from plugins.YouTube.importer import YouTubeImporter
from plugins.YouTube.movie_importer import YouTubeMovieImporter
from plugins.YouTube.music_importer import (
    YouTubeAlbumImporter,
    YouTubeTopicImporter,
)
from plugins.YouTube.playlist_importer import YouTubePlaylistImporter
from plugins.YouTube.series_importer import YouTubeTVShowImporter
from plugins.YouTube.shared import YouTubeShared
from plugins.YouTube.url_parser import YouTubeURLParser
from plugins.YouTube.utils import (
    is_an_album,
    is_quota_error,
    is_title_key,
    is_topic_channel,
    is_user_playlist,
    is_video_key,
)

if TYPE_CHECKING:
    from app.channels.models import ChannelQueue
    from app.titles.models import Title


# TODO: Validate
class YouTubeInitializer(BasePluginInitializer, YouTubeShared): ...


# TODO: Validate
class YouTube(YouTubeShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = YouTubeInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return URL_REGEXES

    # Every address carries the domain it is written under, because a video is
    # named on the long domain and the short one alike, so the domain is not put
    # in front of them here the way it is for every other plugin.
    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        alternatives = "|".join(
            # Strip named groups to non-capturing so addresses that share a group name
            # (e.g. playlist_key) do not collide when the alternatives are combined.
            re.sub(r"\(\?P<[^>]+>", "(?:", url_regex)
            for url_regex in cls._url_regexes()
        )
        return f"(?:{alternatives})"

    # TODO: Validate
    def media_importer_from_title_key(self, title_key: str) -> YouTubeImporter:
        if is_video_key(title_key):
            return YouTubeMovieImporter(self)
        if is_title_key(title_key):
            return YouTubeTVShowImporter(self)
        if is_an_album(title_key):
            return YouTubeAlbumImporter(self)
        if is_user_playlist(title_key):
            return YouTubePlaylistImporter(self)
        if is_topic_channel(self.channel_by_channel_id_file(title_key)):
            return YouTubeTopicImporter(self)
        return YouTubeChannelImporter(self)

    # TODO: Validate
    @override
    def media_importer_from_url(self, url: str) -> YouTubeImporter:
        parser = YouTubeURLParser(self)
        parser.parse(url)
        return self.media_importer_from_title_key(parser.title_key)

    # TODO: Validate
    @override
    def media_importer_from_title(self, title: Title) -> YouTubeImporter:
        if title.media_type == "YouTube Artist":
            return YouTubeTopicImporter(self)
        return self.media_importer_from_title_key(title.key)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        playlist_feed = self.playlist_feed_file(season.key)

        # PlaylistFeed is not a required file because sometimes it will return 404
        # errors for hours at a time.
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
