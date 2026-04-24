# YouTube feeds are extremely flaky so they are not used as the main method for setting
# update_at values, but when they are functional they can be used to detect new episodes
# much faster than using the API because it requires no API calls.
import sys
import time
from datetime import timedelta

from loguru import logger
from sqlmodel import Session, col, select

from app.database import engine, load_models
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

CHECK_INTERVAL_SECONDS = 60 * 60


def main() -> None:
    while True:
        logger.info("Starting YouTube RSS check cycle")
        with Session(engine) as session:
            plugin_instance = YouTube(session)
            youtube_plugin = plugin_instance.plugin

            seasons = session.exec(
                select(Season)
                .join(Show)
                .join(Source)
                .where(
                    Source.plugin_id == youtube_plugin.id,
                    col(Season.deleted_at).is_(None),
                ),
            ).all()
            logger.info(f"Checking {len(seasons)} YouTube seasons")

            for season in seasons:
                try:
                    feed = PlaylistFeed(session, youtube_plugin, season.key)
                    feed.download_if_outdated()
                    if feed.data_timestamp > tz_datetime.now() - timedelta(hours=1):
                        continue

                    old_entries = feed.entries()
                    feed.download_if_outdated(tz_datetime.now())
                    new_entries = feed.entries()

                    if old_entries is None:
                        continue

                    if old_entries == new_entries:
                        continue

                    logger.info(f"RSS entries changed for season {season.key}")
                    season.update_at = tz_datetime.now()

                # TODO: Better error detection which must be done while the RSS feed is
                # broken.
                except Exception:  # noqa: BLE001
                    logger.exception(f"Failed to check RSS for season {season.key}")

            session.commit()
        logger.info(f"Sleeping {CHECK_INTERVAL_SECONDS}s until next cycle")
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
