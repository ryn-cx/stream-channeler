# TODO: Validate
"""The hourly update run YouTube has of its own.

YouTube is left out of `update_outdated` because updating its seasons one at a
time spends a request per playlist on videos that would have fitted in the same
request. Every outdated season of a run is read here together, so the videos all
of them turned up are downloaded at once.
"""

import time
from collections.abc import Sequence
from datetime import timedelta

from loguru import logger
from sqlalchemy.orm import contains_eager
from sqlmodel import Session, col

from app.database import engine, load_models
from app.log import configure_logging
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.tools.update_outdated import _season_in_channel_exists
from app.utils import tz_datetime
from plugins.utils.manage_plugins import import_plugins
from plugins.YouTube import YouTube
from plugins.YouTube.utils import (
    batch_download_missing_videos,
    is_an_album,
    is_video_key,
)

logger = logger.bind(source="updater")

import_plugins()
load_models()


# TODO: Validate
def _is_title_key(key: str) -> bool:
    """Report whether a key belongs to a title page."""
    return key.startswith("SC")


# TODO: Validate
def _belongs_to_a_channel(season: Season) -> bool:
    """Report whether a season is the uploads of, or a playlist of, a channel.

    A title that is a single video and a title read off a title page are titles
    without a channel behind them, and neither has a feed for the run to ask
    what was added, so neither is what this update is for.
    """
    title_key = season.title.key
    return (
        not is_video_key(title_key)
        and not _is_title_key(title_key)
        and not is_an_album(title_key)
        # A release is a season of the musician's Topic channel, and YouTube
        # serves no feed for one, so it is no more this run's than an album
        # imported on its own is.
        and not is_an_album(season.key)
    )


# TODO: Validate
def _outdated_title_seasons(session: Session) -> list[Season]:
    statement = (
        Season.select_with_plugin()
        .where(
            col(Plugin.key) == YouTube.plugin_name(),
            col(Season.update_at).is_not(None),
            col(Season.update_at) < tz_datetime.now(),
            col(Season.deleted_at).is_(None),
            _season_in_channel_exists(),
        )
        .options(contains_eager(Season.title))  # type: ignore[arg-type]
        .order_by(col(Season.update_at).asc())
    )
    return [
        season
        for season in session.exec(statement).unique().all()
        if _belongs_to_a_channel(season)
    ]


# TODO: Validate
def _seasons_with_new_videos(
    plugin: YouTube, seasons: Sequence[Season]
) -> list[Season]:
    """Read every season's feed and return the ones that gained videos.

    Every feed is read before anything is updated so the videos they turned up
    can be asked for in one request rather than one per season.
    """
    changed: list[Season] = []
    for season in seasons:
        playlist_feed = plugin.playlist_feed_file(season.key)
        # PlaylistFeed is not a required file because sometimes it will return 404
        # errors for hours at a time so an initial file may need to be downloaded here.
        if playlist_feed.does_not_exist():
            playlist_feed.download_if_outdated()
            continue

        old_video_ids = playlist_feed.video_ids()
        playlist_feed.download_if_outdated(season.update_at)
        season.update_at = playlist_feed.record_data_timestamp + timedelta(hours=6)

        if new_video_ids := playlist_feed.video_ids() - old_video_ids:
            logger.info(
                "Found {} new videos in season {}: {}",
                len(new_video_ids),
                season.name or season.key,
                ", ".join(sorted(new_video_ids)),
            )
            changed.append(season)
    return changed


# TODO: Validate
def _download_videos(plugin: YouTube, seasons: Sequence[Season]) -> None:
    """Download every video the changed seasons name in one batch."""
    video_keys: dict[str, None] = {}
    for season in seasons:
        for video_key in plugin.playlist_feed_file(season.key).video_ids():
            video_keys[video_key] = None
    batch_download_missing_videos(
        [plugin.videos_file(video_key) for video_key in video_keys],
    )


# TODO: Validate
def update_youtube() -> None:
    with Session(engine) as session:
        seasons = _outdated_title_seasons(session)
        if not seasons:
            logger.info("[YouTube] No outdated title seasons")
            return

        log_msg = f"[YouTube] Found {len(seasons)} outdated title seasons"
        logger.info(log_msg)
        plugin = YouTube(session, seasons[0].title.source.plugin)
        try:
            changed = _seasons_with_new_videos(plugin, seasons)
            session.commit()
            _download_videos(plugin, changed)
            for season in changed:
                plugin.update_title(season.title)
            session.commit()
        except Exception:
            logger.exception("[YouTube] Update run failed")
            session.rollback()
            for season in seasons:
                session.refresh(season)
                season.update_at = tz_datetime.now() + timedelta(hours=1)
            session.commit()
            return

        log_msg = f"[YouTube] Updated {len(seasons)} title seasons"
        logger.info(log_msg)


# TODO: Validate
UPDATE_INTERVAL = 60.0 * 60.0 * 24


# TODO: Validate
def run_forever() -> None:
    while True:
        update_youtube()
        log_msg = f"[YouTube] Next update run in {UPDATE_INTERVAL:.0f}s"
        logger.info(log_msg)
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    configure_logging()
    run_forever()
