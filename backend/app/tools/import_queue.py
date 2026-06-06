# TODO: Validate

import traceback

from loguru import logger
from sqlmodel import Session, col, select

from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelQueue,
    ChannelSeasonFilter,
    ChannelShow,
    URLStatus,
)
from app.database import engine, automatically_import_models
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
automatically_import_models()


def import_queue(session: Session) -> None:
    statement = select(ChannelQueue).where(
        col(ChannelQueue.status).in_([URLStatus.PENDING, URLStatus.IMPORTING]),
    )
    results = session.exec(statement)
    queue_items = list(results)

    # Move YouTube URLs to the end of the queue
    youtube_items = [item for item in queue_items if "youtube.com" in item.url.lower()]
    non_youtube_items = [
        item for item in queue_items if "youtube.com" not in item.url.lower()
    ]
    queue_items = non_youtube_items + youtube_items

    # Each item runs in its own transaction so a failure marks just that item
    # as FAILED without rolling back other items, and the FAILED status is
    # persisted (avoiding infinite retries from the SELECT above).
    for queue_item in queue_items:
        logger.info(f"Importing URL: {queue_item.url}")
        for plugin in plugins:
            if not plugin.is_valid_url_format(queue_item.url):
                continue
            if not plugin.implements("import_url"):
                continue
            try:
                queue_item.status = URLStatus.IMPORTING
                plugin_instance = plugin(session)
                import_results = plugin_instance.import_url(queue_item.url)
                add_results_to_channel(session, import_results, queue_item.channel)
            except InvalidURLError:
                logger.warning(f"Invalid URL {plugin.__name__}: {queue_item.url}")
                note = "Invalid URL."
            # BLE001 - capture all exceptions so one bad URL can't stall the queue.
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    f"Error importing {plugin.__name__}: {queue_item.url}",
                )
                # Rollback first so partial import work is discarded, then
                # re-mark FAILED on the now-expired row so the next commit
                # actually persists the status.
                session.rollback()
                note = "".join(
                    traceback.format_exception(type(e), e, e.__traceback__),
                )
            else:
                queue_item.status = URLStatus.IMPORTED
                session.commit()
                break
            queue_item.status = URLStatus.FAILED
            queue_item.note = note
            session.commit()
            break
        else:
            logger.warning(f"No valid plugin found for URL: {queue_item.url}")
            queue_item.status = URLStatus.FAILED
            queue_item.note = "No valid plugin found."
            session.commit()


def add_results_to_channel(
    session: Session,
    results: list[URLImportResult],
    channel: Channel,
) -> None:
    existing_channel_shows = {show.show_id: show for show in channel.shows}
    for result in results:
        if existing_channel_show := existing_channel_shows.get(result.show.id):
            _extend_channel_show(session, existing_channel_show, result)
        else:
            _create_channel_show(session, channel, result)


def _create_channel_show(
    session: Session,
    channel: Channel,
    result: URLImportResult,
) -> None:
    channel_show = ChannelShow(
        channel_id=channel.id,
        show_id=result.show.id,
        is_whitelist=result.is_whitelist,
    )
    channel.shows.append(channel_show)

    for season in result.seasons:
        session.add(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season.id,
            ),
        )

    for episode in result.episodes:
        session.add(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode.id,
            ),
        )


def _extend_channel_show(
    session: Session,
    existing_channel_show: ChannelShow,
    result: URLImportResult,
) -> None:
    visible_season_ids = {season.id for season in result.seasons}
    visible_episode_ids = {episode.id for episode in result.episodes}

    if existing_channel_show.is_whitelist:
        existing_season_ids = {
            season_filter.season_id
            for season_filter in existing_channel_show.season_filters
        }
        for season_id in visible_season_ids - existing_season_ids:
            session.add(
                ChannelSeasonFilter(
                    channel_show_id=existing_channel_show.id,
                    season_id=season_id,
                ),
            )
        existing_episode_ids = {
            episode_filter.episode_id
            for episode_filter in existing_channel_show.episode_filters
        }
        for episode_id in visible_episode_ids - existing_episode_ids:
            session.add(
                ChannelEpisodeFilter(
                    channel_show_id=existing_channel_show.id,
                    episode_id=episode_id,
                ),
            )
        return

    for season_filter in list(existing_channel_show.season_filters):
        if season_filter.season_id in visible_season_ids:
            session.delete(season_filter)
    for episode_filter in list(existing_channel_show.episode_filters):
        if episode_filter.episode_id in visible_episode_ids:
            session.delete(episode_filter)


if __name__ == "__main__":
    with Session(engine) as session:
        import_queue(session)
