# TODO: Validate
"""Updating every outdated channel season of a run together."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from app.utils import tz_datetime
from plugins.YouTube.constants import FEED_UPDATE_DELAY
from plugins.YouTube.files import FileMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.seasons.models import Season
    from app.shows.models import Show


# TODO: Validate
class UpdaterMixin(FileMixin, register=False):
    """Updating channel seasons in one pass rather than one at a time."""

    # TODO: Validate
    def update_channel_seasons(self, seasons: Sequence[Season]) -> None:
        """Bring every outdated channel season up to date together.

        Each season's feed is read first, because a feed says whether anything
        was added without spending quota on the playlist itself. Only the
        seasons the feed named something new for are read again, and the videos
        every one of them turned up are downloaded in a single batch, so a run
        covering fifty playlists costs the same requests as the videos would
        have cost had they all been in one.
        """
        changed_seasons = [
            season for season in seasons if self._refresh_season_listing(season)
        ]
        if not changed_seasons:
            return

        seasons_by_show: dict[Show, list[Season]] = {}
        for season in changed_seasons:
            seasons_by_show.setdefault(season.show, []).append(season)

        video_keys: list[str] = []
        for show, show_seasons in seasons_by_show.items():
            season_keys = [season.key for season in show_seasons]
            self._set_current_show(show.key)
            _cache = self._preload_all_episode_files(season_keys, show.key)
            for season_key in season_keys:
                video_keys.extend(
                    key
                    for key in self._episode_keys_from_file(season_key, show.key)
                    if key not in video_keys
                )

        self._batch_download_videos(video_keys)

        for show in seasons_by_show:
            self._set_current_show(show.key)
            self._update_and_upsert_show(show)

    # TODO: Validate
    def _refresh_season_listing(self, season: Season) -> bool:
        """Read a season's feed, and its listing again when the feed named a video.

        Returns whether the listing was read again, which is what decides
        whether the season's videos are part of the run's batch.
        """
        self._set_current_show(season.show.key)
        playlist_feed = self.playlist_feed_file(season.key)
        # Without a stored feed there is nothing to compare the download against, so
        # this run only stores the feed and the next one checks it for new videos.
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
            season.update_at = tz_datetime.now() + FEED_UPDATE_DELAY
            return False

        season.update_at = playlist_feed.data_timestamp + FEED_UPDATE_DELAY
        if not has_stored_feed:
            return False

        new_video_ids = set(playlist_feed.video_ids()) - old_video_ids
        if not new_video_ids:
            return False

        logger.info(
            "Found {} new videos in season {}: {}",
            len(new_video_ids),
            season.key,
            ", ".join(sorted(new_video_ids)),
        )
        self._download_outdated_files(
            self._season_files(season.key, season.show.key),
            tz_datetime.now(),
        )
        return True
