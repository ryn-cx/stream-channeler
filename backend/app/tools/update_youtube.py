# TODO: Validate
"""The hourly update run YouTube has of its own.

YouTube is left out of `update_outdated` because updating its seasons one at a
time spends a request per playlist on videos that would have fitted in the same
request. Every outdated season of a run is read here together, so the videos all
of them turned up are downloaded at once.
"""

import time
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import timedelta

from loguru import logger
from not_yt_dlapi.exceptions import (
    ChannelFeedNotFoundError,
    PlaylistFeedNotFoundError,
)
from sqlalchemy.orm import contains_eager
from sqlmodel import Session, col, select

from app.database import engine, load_models
from app.episodes.models import Episode
from app.log import configure_logging
from app.media.service.updating import update_record
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.titles.models import Title
from app.tools.update_outdated import (
    _season_in_channel_exists,
    _title_has_season_in_channel_exists,
)
from app.utils import tz_datetime
from plugins.utils.manage_plugins import import_plugins
from plugins.YouTube import YouTube
from plugins.YouTube.shared import (
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
def _outdated_titles(session: Session) -> list[Title]:
    statement = (
        Title.select_with_plugin()
        .where(
            col(Plugin.key) == YouTube.plugin_name(),
            col(Title.update_at).is_not(None),
            col(Title.update_at) < tz_datetime.now(),
            col(Title.deleted_at).is_(None),
            _title_has_season_in_channel_exists(),
        )
        .order_by(col(Title.update_at).asc())
    )
    return [
        title
        for title in session.exec(statement).unique().all()
        if not is_video_key(title.key)
        and not _is_title_key(title.key)
        and not is_an_album(title.key)
    ]


# TODO: Validate
def _imported_episode_keys(
    session: Session,
    seasons: Sequence[Season],
) -> defaultdict[uuid.UUID, set[str]]:
    """Return the keys of every episode each season already holds."""
    imported: defaultdict[uuid.UUID, set[str]] = defaultdict(set)
    season_ids = [season.id for season in seasons]
    if not season_ids:
        return imported
    rows = session.exec(
        select(col(Episode.season_id), col(Episode.key)).where(
            col(Episode.season_id).in_(season_ids),
        ),
    ).all()
    for season_id, episode_key in rows:
        imported[season_id].add(episode_key)
    return imported


# TODO: Validate
def _seasons_with_new_videos(
    plugin: YouTube,
    session: Session,
    seasons: Sequence[Season],
) -> list[Season]:
    imported = _imported_episode_keys(session, seasons)
    changed: list[Season] = []
    for season in seasons:
        playlist_feed = plugin.playlist_feed_file(season.key)
        try:
            # PlaylistFeed is not a required file because sometimes it will return 404
            # errors for hours at a time so an initial file may need to be downloaded here.
            if playlist_feed.does_not_exist():
                playlist_feed.download_if_outdated()
                continue

            playlist_feed.download_if_outdated(season.update_at)
        except (ChannelFeedNotFoundError, PlaylistFeedNotFoundError) as error:
            plugin.on_update_season_failure(season, error)
            continue
        season.update_at = playlist_feed.record_data_timestamp + timedelta(days=1)

        if new_video_ids := playlist_feed.video_ids() - imported[season.id]:
            logger.info(
                "Found {} new videos in season {}: {}",
                len(new_video_ids),
                season.name or season.key,
                ", ".join(sorted(new_video_ids)),
            )
            changed.append(season)
    return changed


# TODO: Validate
def _refresh_playlist_items(plugin: YouTube, seasons: Sequence[Season]) -> None:
    """Read the playlist of every changed season again."""
    for season in seasons:
        plugin.playlist_items_file(season.key).download_if_outdated(
            tz_datetime.now(),
        )


# TODO: Validate
def _download_videos(plugin: YouTube, seasons: Sequence[Season]) -> None:
    """Download every video the changed seasons name in one batch."""
    video_keys: dict[str, None] = {}
    for season in seasons:
        for video_key in plugin.playlist_season_episode_keys(season):
            video_keys[video_key] = None
    plugin.download_missing_videos(video_keys)


# TODO: Validate
def update_youtube() -> None:
    with Session(engine, expire_on_commit=False) as session:
        seasons = _outdated_title_seasons(session)
        titles = _outdated_titles(session)
        if not seasons and not titles:
            logger.info("[YouTube] No outdated title seasons")
            return

        log_msg = (
            f"[YouTube] Found {len(seasons)} outdated title seasons "
            f"and {len(titles)} outdated titles"
        )
        logger.info(log_msg)
        plugin = YouTube(session)
        try:
            changed = _seasons_with_new_videos(plugin, session, seasons)
            session.commit()
            _refresh_playlist_items(plugin, changed)
            _download_videos(plugin, changed)
            for season in changed:
                plugin.update_playlist_season(season)
            session.commit()
        except Exception:
            logger.exception("[YouTube] Season update run failed")
            session.rollback()
            for season in seasons:
                session.refresh(season)
                season.update_at = tz_datetime.now() + timedelta(hours=1)
            session.commit()
        else:
            log_msg = f"[YouTube] Updated {len(seasons)} title seasons"
            logger.info(log_msg)

        for title in titles:
            update_record(session, plugin, YouTube.plugin_name(), title)


# TODO: Validate
UPDATE_INTERVAL = 60.0 * 60.0


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
