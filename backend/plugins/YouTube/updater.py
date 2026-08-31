# TODO: Validate
"""Updating every outdated show season of a run together."""

from __future__ import annotations

from contextlib import suppress
from datetime import timedelta
from typing import TYPE_CHECKING

from loguru import logger
from not_yt_dlapi.exceptions import (
    ChannelFeedNotFoundError,
    PlaylistFeedNotFoundError,
)
from sqlmodel import col

from app.plugins.models import Plugin
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.utils.base_plugin_v2.files import EXTRA_STATUS_FIELD
from plugins.YouTube.files import FileMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugins.YouTube.files import PlaylistFeed

PENDING_UPDATE_STATUS = "Pending update"


# TODO: Validate
class UpdaterMixin(FileMixin):
    def update_seasons(self, seasons: Sequence[Season]) -> None:
        """Update multiple seasons at once to reduce the number of API calls."""
        for season in seasons:
            self.check_feed_for_new_files(season)
            self.session.commit()

        self._update_marked_seasons()

    # TODO: Validate
    def _update_marked_seasons(self) -> None:
        seasons = self._season_with_new_episodes_available()

        video_keys: list[str] = []
        for season in seasons:
            video_keys.extend(
                key
                for key in self._episode_keys_from_file(season.key, season.show.key)
                if key not in video_keys
            )

        self._batch_download_missing_videos(video_keys)

        for season in seasons:
            self._update_and_upsert_show(season.show)
            season.extra = {
                field: value
                for field, value in season.extra.items()
                if field != EXTRA_STATUS_FIELD
            }
            self.session.commit()
            self.clear_file_cache()

    # TODO: Validate
    def _season_with_new_episodes_available(self) -> list[Season]:
        statement = Season.select_with_plugin_eager().where(
            col(Plugin.key) == self.plugin_name(),
            col(Season.deleted_at).is_(None),
            col(Season.extra)[EXTRA_STATUS_FIELD].astext == PENDING_UPDATE_STATUS,
        )
        return list(self.session.exec(statement).unique().all())

    # TODO: Validate
    def check_feed_for_new_files(self, season: Season) -> None:
        playlist_feed = self.playlist_feed_file(season.key)

        # If the file does not exist just download the initial file. The first update
        # will be delayed a bit but it's acceptable for code that is easier to work with.
        if playlist_feed.does_not_exist():
            with suppress(ChannelFeedNotFoundError, PlaylistFeedNotFoundError):
                self._download_season_feed(season)
            return

        old_feed_video_ids = set(playlist_feed.video_ids())
        try:
            self._download_season_feed(season)
        except ChannelFeedNotFoundError, PlaylistFeedNotFoundError:
            return

        new_video_ids = set(playlist_feed.video_ids()) - old_feed_video_ids
        if not new_video_ids:
            return

        logger.info(
            "Found {} new videos in season {}: {}",
            len(new_video_ids),
            season.name or season.key,
            ", ".join(sorted(new_video_ids)),
        )
        season.extra = {**season.extra, EXTRA_STATUS_FIELD: PENDING_UPDATE_STATUS}
        self.playlist_items_file(season.key).download_if_outdated(tz_datetime.now())

    # TODO: Validate
    def _download_season_feed(self, season: Season) -> PlaylistFeed:
        playlist_feed = self.playlist_feed_file(season.key)
        try:
            playlist_feed.download_if_outdated(season.update_at)
        except ChannelFeedNotFoundError, PlaylistFeedNotFoundError:
            season.update_at = tz_datetime.now() + timedelta(hours=1)
            raise

        season.update_at = playlist_feed.data_timestamp + timedelta(hours=6)
        return playlist_feed
