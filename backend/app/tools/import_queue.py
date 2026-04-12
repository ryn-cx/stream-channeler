# TODO: Validate

import traceback

from loguru import logger
from sqlmodel import Session, col, select

from app.channels.models import (
    Channel,
    ChannelEpisodeWhiteList,
    ChannelQueue,
    ChannelSeasonWhiteList,
    ChannelShow,
    URLStatus,
)
from app.database import engine, load_models
from app.plugins.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from app.plugins.plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


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

    for queue_item in queue_items:
        logger.info(f"Importing URL: {queue_item.url}")
        for plugin in plugins:
            if plugin.is_valid_url_format(queue_item.url):
                try:
                    queue_item.status = URLStatus.IMPORTING
                    plugin_instance = plugin(session)
                    import_results = plugin_instance.import_url(queue_item.url)
                    add_results_to_channel(session, import_results, queue_item.channel)
                    queue_item.status = URLStatus.IMPORTED
                    break
                except InvalidURLError:
                    logger.warning(
                        f"Invalid URL {plugin.__name__}: {queue_item.url}",
                    )
                    queue_item.status = URLStatus.FAILED
                    queue_item.note = "Invalid URL."
                    break

                # BLE001 - This needs to be able to capture all exceptions to work correctly.
                except Exception as e:  # noqa: BLE001
                    logger.exception(
                        f"Error importing {plugin.__name__}: {queue_item.url}",
                    )
                    queue_item.status = URLStatus.FAILED
                    queue_item.note = "".join(
                        traceback.format_exception(type(e), e, e.__traceback__),
                    )
                    session.rollback()
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
    existing_show_ids = {show.show_id for show in channel.shows}
    for result in results:
        # If a ChannelShow already exists for this show, leave it untouched.
        if result.show.id in existing_show_ids:
            continue

        channel_show = ChannelShow(
            channel_id=channel.id,
            show_id=result.show.id,
            white_list_mode=result.whitelist_mode,
        )
        channel.shows.append(channel_show)

        for season in result.seasons:
            session.add(
                ChannelSeasonWhiteList(
                    channel_show_id=channel_show.id,
                    season_id=season.id,
                ),
            )

        for episode in result.episodes:
            session.add(
                ChannelEpisodeWhiteList(
                    channel_show_id=channel_show.id,
                    episode_id=episode.id,
                ),
            )


if __name__ == "__main__":
    with Session(engine) as session:
        import_queue(session)
