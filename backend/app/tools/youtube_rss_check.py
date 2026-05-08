"""Set Season.update_at values based on new videos found in YouTube's RSS feeds.

YouTube RSS feeds are extremely flaky so they should not be used as the only method for
setting update_at values because they might be deprecated at some point in the future.
"""

import sys
from datetime import timedelta
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import or_
from sqlmodel import Session, col, func, select

from app.channels.models import ChannelSeasonFilter, ChannelShow

if TYPE_CHECKING:
    from sqlmodel.sql.expression import SelectOfScalar
from app.database import engine, load_models
from app.plugins.models import File
from app.plugins.plugins.utils.manage_plugins import import_plugins
from app.plugins.plugins.YouTube import YouTube
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


def _playlist_feed_base_query(youtube_plugin_id: object) -> SelectOfScalar[Season]:
    return (
        select(Season)
        .join(Show)
        .join(Source)
        .outerjoin(
            File,
            (col(File.plugin_id) == youtube_plugin_id)
            & (col(File.key) == func.concat("PlaylistFeed/", col(Season.key), ".xml")),
        )
        .where(
            Source.plugin_id == youtube_plugin_id,
            col(Season.deleted_at).is_(None),
        )
    )


def _new_seasons(
    session: Session,
    youtube_plugin_id: object,
) -> list[Season]:
    # Unlike _outdated_seasons, it does not matter if a season exists in a channel
    # because an initial file needs to exist to support a user adding an existing
    # season to a channel properly. The initial file will allow this script to
    # immediately detect any new videos that were adding to the playlist. Without this
    # the user would have to wait until a new video is added to the playlist for the
    # season to be updated.
    return list(
        session.exec(
            _playlist_feed_base_query(youtube_plugin_id).where(
                col(File.id).is_(None),
            ),
        ).all(),
    )


def _outdated_seasons(
    session: Session,
    youtube_plugin_id: object,
) -> list[Season]:
    return list(
        session.exec(
            _playlist_feed_base_query(youtube_plugin_id).where(
                col(File.update_at) < tz_datetime.now(),
                # Only select seasons that are in a channel because there is no reason
                # to update unused seasons.
                (
                    select(ChannelShow.id)
                    .outerjoin(
                        ChannelSeasonFilter,
                        (
                            col(ChannelSeasonFilter.channel_show_id)
                            == col(ChannelShow.id)
                        )
                        & (col(ChannelSeasonFilter.season_id) == col(Season.id)),
                    )
                    .where(
                        col(ChannelShow.show_id) == col(Season.show_id),
                        or_(
                            col(ChannelShow.is_whitelist).is_(True)
                            & col(ChannelSeasonFilter.season_id).is_not(None),
                            col(ChannelShow.is_whitelist).is_(False)
                            & col(ChannelSeasonFilter.season_id).is_(None),
                        ),
                    )
                    .exists()
                ),
            ),
        ).all(),
    )


def _download_initial_files(session: Session, youtube_plugin_id: object) -> None:
    new_seasons = _new_seasons(session, youtube_plugin_id)
    logger.info(f"Downloading {len(new_seasons)} initial RSS feeds.")
    for season in new_seasons:
        playlist_feed = YouTube(session).playlist_feed_file(season.key)
        try:
            playlist_feed.download_if_outdated()
        # TODO: Better error detection which must be done while the RSS feed is broken.
        except Exception:  # noqa: BLE001
            # Initial files are allowed to be blank due to the unreliability of
            # YouTube's RSS feeds.
            logger.exception(f"{season.key}: Failed to download initial RSS feed.")

        new_update_at = playlist_feed.data_timestamp + timedelta(hours=1)
        playlist_feed.database_record.set_update_at(new_update_at)
        session.commit()


def _check_for_updates(session: Session, youtube_plugin_id: object) -> None:
    outdated_seasons = _outdated_seasons(session, youtube_plugin_id)
    logger.info(f"Updating {len(outdated_seasons)} outdated RSS feeds.")
    for season in outdated_seasons:
        playlist_feed = YouTube(session).playlist_feed_file(season.key)

        # The initial file is allowed to be blank so check if it has content before
        # calling video_ids.
        if playlist_feed.database_record.content:
            old_video_ids = set(playlist_feed.video_ids())
        else:
            old_video_ids: set[str] = set()

        try:
            playlist_feed.download_if_outdated(tz_datetime.now())
        # TODO: Better error detection which must be done while the RSS feed is broken.
        except Exception:  # noqa: BLE001
            logger.exception(f"{season.key}: Failed to download updated RSS feed.")
        else:
            # Do not check for equality because this is checking only for new videos,
            # if a video is removed no update needs to be done.
            if new_video_ids := set(playlist_feed.video_ids()) - old_video_ids:
                logger.info(
                    f"{season.key}: {len(new_video_ids)} new videos detected "
                    f"({', '.join(new_video_ids)})",
                )
                season.set_update_at(tz_datetime.now())

        new_update_at = playlist_feed.data_timestamp + timedelta(hours=1)
        playlist_feed.database_record.set_update_at(new_update_at)
        session.commit()


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, level="INFO", colorize=True)

    import_plugins()
    load_models()

    with Session(engine) as session:
        youtube_plugin_id = YouTube(session).plugin.id
        _download_initial_files(session, youtube_plugin_id)
        _check_for_updates(session, youtube_plugin_id)
