# TODO: Validate
"""The hourly update run YouTube has of its own.

YouTube is left out of `update_outdated` because updating its seasons one at a
time spends a request per playlist on videos that would have fitted in the same
request. Every outdated season of a run is read here together, so the videos all
of them turned up are downloaded at once.
"""

import time

from loguru import logger
from sqlalchemy.orm import contains_eager
from sqlmodel import Session, col

from app.database import engine, load_models
from app.log import configure_logging
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.utils.manage_plugins import import_plugins
from plugins.YouTube import YouTube
from plugins.YouTube.files import is_an_album, is_show_key, is_video_key

logger = logger.bind(source="updater")

import_plugins()
load_models()

UPDATE_INTERVAL_SECONDS = 60.0 * 60.0


# TODO: Validate
def _belongs_to_a_channel(season: Season) -> bool:
    """Report whether a season is the uploads of, or a playlist of, a channel.

    A show that is a single video and a show read off a show page are shows
    without a channel behind them, and neither has a feed for the run to ask
    what was added, so neither is what this update is for.
    """
    show_key = season.show.key
    return (
        not is_video_key(show_key)
        and not is_show_key(show_key)
        and not is_an_album(show_key)
        # A release is a season of the musician's Topic channel, and YouTube
        # serves no feed for one, so it is no more this run's than an album
        # imported on its own is.
        and not is_an_album(season.key)
    )


# TODO: Validate
def _outdated_channel_seasons(session: Session) -> list[Season]:
    statement = (
        Season.select_with_plugin()
        .where(
            col(Plugin.key) == YouTube.plugin_key(),
            col(Season.update_at).is_not(None),
            col(Season.update_at) < tz_datetime.now(),
            col(Season.deleted_at).is_(None),
        )
        .options(contains_eager(Season.show))  # type: ignore[arg-type]
        .order_by(col(Season.update_at).asc())
    )
    return [
        season
        for season in session.exec(statement).unique().all()
        if _belongs_to_a_channel(season)
    ]


# TODO: Validate
def update_youtube() -> None:
    """Update every outdated channel season in one pass."""
    with Session(engine) as session:
        seasons = _outdated_channel_seasons(session)
        if not seasons:
            logger.info("[YouTube] No outdated channel seasons")
            return

        log_msg = f"[YouTube] Found {len(seasons)} outdated channel seasons"
        logger.info(log_msg)
        plugin = YouTube(session)
        try:
            plugin.update_channel_seasons(seasons)
            session.commit()
        except Exception as error:
            logger.exception("[YouTube] Update run failed")
            session.rollback()
            for season in seasons:
                session.refresh(season)
                plugin.on_update_season_failure(season, error)
            session.commit()
            return

        log_msg = f"[YouTube] Updated {len(seasons)} channel seasons"
        logger.info(log_msg)


# TODO: Validate
def run_forever() -> None:
    """Update every outdated channel season, once an hour, forever."""
    while True:
        try:
            update_youtube()
        except Exception:
            logger.exception("[YouTube] Update run crashed")
        log_msg = f"[YouTube] Next update run in {UPDATE_INTERVAL_SECONDS:.0f}s"
        logger.info(log_msg)
        time.sleep(UPDATE_INTERVAL_SECONDS)


if __name__ == "__main__":
    configure_logging()
    run_forever()
