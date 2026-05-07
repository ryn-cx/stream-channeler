# TODO: Validate
# YouTube feeds are extremely flaky so they are not used as the main method for setting
# update_at values, but when they are functional they can be used to detect new episodes
# much faster than using the API because it requires no API calls.
import sys
import time
from datetime import timedelta

from loguru import logger
from sqlmodel import Session, col, func, select

from app.database import engine, load_models
from app.plugins.models import File
from app.plugins.plugins.utils.manage_plugins import import_plugins
from app.plugins.plugins.YouTube import YouTube
from app.plugins.plugins.YouTube.files import PlaylistFeed
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime

logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True)

import_plugins()
load_models()


def _seasons_needing_check(
    session: Session,
    youtube_plugin_id: object,
    *,
    has_existing_file: bool,
) -> list[str]:
    one_hour_ago = tz_datetime.now() - timedelta(hours=1)
    playlist_feed_key = func.concat("PlaylistFeed/", col(Season.key), ".xml")
    join_condition = (col(File.plugin_id) == youtube_plugin_id) & (
        col(File.key) == playlist_feed_key
    )
    file_condition = (
        col(File.data_timestamp) < one_hour_ago
        if has_existing_file
        else col(File.id).is_(None)
    )
    return list(
        session.exec(
            select(Season.key)
            .join(Show)
            .join(Source)
            .outerjoin(File, join_condition)
            .where(
                Source.plugin_id == youtube_plugin_id,
                col(Season.deleted_at).is_(None),
                file_condition,
            ),
        ).all(),
    )


def _initial_import(session: Session, youtube_plugin_id: object) -> None:
    season_keys = _seasons_needing_check(
        session,
        youtube_plugin_id,
        has_existing_file=False,
    )
    logger.info(f"Initial-import pass: {len(season_keys)} seasons")
    for season_key in season_keys:
        try:
            youtube_plugin = YouTube(session).plugin
            feed = PlaylistFeed(session, youtube_plugin, season_key)
            feed.download_if_outdated()
            logger.info(f"Initial feed download for {season_key}")
        # TODO: Better error detection which must be done while the RSS feed is broken.
        except Exception:
            logger.exception(f"Failed initial RSS fetch for {season_key}")
        finally:
            session.commit()


def _check_for_updates(session: Session, youtube_plugin_id: object) -> None:
    season_keys = _seasons_needing_check(
        session,
        youtube_plugin_id,
        has_existing_file=True,
    )
    logger.info(f"Update pass: {len(season_keys)} stale seasons")
    for season_key in season_keys:
        try:
            youtube_plugin = YouTube(session).plugin
            feed = PlaylistFeed(session, youtube_plugin, season_key)
            old_video_ids = set(feed.video_ids())
            feed.download_if_outdated(tz_datetime.now())

            if not (new_video_ids := set(feed.video_ids()) - old_video_ids):
                logger.info(f"Skipping {season_key}: no new video IDs")
                continue

            logger.info(
                f"New videos detected for season {season_key} "
                f"(+{len(new_video_ids)}):\n  " + "\n  ".join(new_video_ids),
            )
        # TODO: Better error detection which must be done while the RSS feed is broken.
        except Exception:  # noqa: BLE001
            logger.exception(f"Failed to check RSS for season {season_key}")
        finally:
            session.commit()


def main() -> None:
    logger.info("Starting YouTube RSS check cycle")
    with Session(engine) as session:
        youtube_plugin_id = YouTube(session).plugin.id
        _initial_import(session, youtube_plugin_id)
        _check_for_updates(session, youtube_plugin_id)


if __name__ == "__main__":
    main()
