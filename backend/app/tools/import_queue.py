# TODO: Validate

import threading
import traceback
from uuid import UUID

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
from app.database import import_models, engine
from app.episodes.models import Episode
from app.log import configure_logging
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.manage_plugins import import_plugins, plugins

logger = logger.bind(source="import_queue")

import_plugins()
PLUGIN_LOCKS = {plugin_class.plugin_key(): threading.Lock() for plugin_class in plugins}


def run_forever(stop_event: threading.Event | None = None) -> None:  # noqa: D103
    stop_event = stop_event or threading.Event()
    while not stop_event.is_set():
        with Session(engine) as session:
            import_queue(session)
        if stop_event.wait(timeout=60):
            break


def import_queue(session: Session) -> None:
    """Actually import the queue in separate threads for each plugin."""
    for plugin_class, items in _group_pending_urls_by_plugin(session).items():
        with PLUGIN_LOCKS[plugin_class.plugin_key()]:
            for item in items:
                _import_one(session, item, plugin_class)


def _get_plugin(url: str) -> type[AbstractPlugin] | None:
    for plugin_class in plugins:
        if plugin_class.is_valid_url_format(url):
            return plugin_class
    return None


def _group_pending_urls_by_plugin(
    session: Session,
) -> dict[type[AbstractPlugin], list[ChannelQueue]]:
    by_plugin: dict[type[AbstractPlugin], list[ChannelQueue]] = {}
    unmatched: list[ChannelQueue] = []
    pending = session.exec(
        select(ChannelQueue)
        .where(col(ChannelQueue.status).in_([URLStatus.PENDING, URLStatus.IMPORTING]))
        .order_by(col(ChannelQueue.created_at).asc()),
    ).all()
    for item in pending:
        if plugin_class := _get_plugin(item.url):
            by_plugin.setdefault(plugin_class, []).append(item)
        elif item.status == URLStatus.PENDING:
            logger.warning(f"No valid plugin found for URL: {item.url}")
            item.status = URLStatus.FAILED
            item.note = "No valid plugin found."
            unmatched.append(item)
    if unmatched:
        session.commit()
    return by_plugin


def _import_one(
    session: Session,
    queue_item: ChannelQueue,
    plugin_class: type[AbstractPlugin],
) -> None:
    """Import a single queue item and commit its final status."""
    plugin_key = plugin_class.plugin_key()
    logger.info(f"[{plugin_key}] Importing URL: {queue_item.url}")
    try:
        queue_item.status = URLStatus.IMPORTING
        import_results = plugin_class(session).import_url(queue_item.url)
        add_results_to_channel(session, import_results, queue_item.channel)
    except InvalidURLError:
        logger.warning(f"[{plugin_key}] Invalid URL: {queue_item.url}")
        queue_item.status = URLStatus.FAILED
        queue_item.note = "Invalid URL."
        session.commit()
    except Exception as error:  # noqa: BLE001
        logger.exception(f"[{plugin_key}] Error importing: {queue_item.url}")
        session.rollback()
        queue_item.status = URLStatus.FAILED
        queue_item.note = "".join(
            traceback.format_exception(type(error), error, error.__traceback__),
        )
        session.commit()
    else:
        queue_item.status = URLStatus.IMPORTED
        session.commit()


def add_results_to_channel(
    session: Session,
    results: list[URLImportResult],
    channel: Channel,
) -> None:
    """Add the given import results to the channel."""
    existing_channel_shows = {show.show_id: show for show in channel.shows}
    for result in results:
        if existing_channel_show := existing_channel_shows.get(result.show.id):
            _update_channel_show(session, existing_channel_show, result)
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
        is_blacklist_only=False,
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


def _update_channel_show(
    session: Session,
    existing_channel_show: ChannelShow,
    result: URLImportResult,
) -> None:
    existing_channel_show.is_blacklist_only = False

    was_whitelist = existing_channel_show.is_whitelist
    existing_season_ids: set[UUID] = {
        season_filter.season_id
        for season_filter in existing_channel_show.season_filters
    }
    existing_episode_ids: set[UUID] = {
        episode_filter.episode_id
        for episode_filter in existing_channel_show.episode_filters
    }
    blacklisted_episode_ids: set[UUID] = (
        set() if was_whitelist else existing_episode_ids
    )

    result_season_ids: set[UUID] = {season.id for season in result.seasons}
    result_episode_ids: set[UUID] = {episode.id for episode in result.episodes}

    if result.is_whitelist:
        season_ids = (
            existing_season_ids if was_whitelist else set[UUID]()
        ) | result_season_ids
        whitelisted_episode_ids = (
            (existing_episode_ids if was_whitelist else set[UUID]())
            | result_episode_ids
        ) - blacklisted_episode_ids
        season_by_blacklisted_episode = _season_ids_for_episodes(
            session,
            blacklisted_episode_ids,
        )
        exclusion_episode_ids = {
            episode_id
            for episode_id, season_id in season_by_blacklisted_episode.items()
            if season_id in season_ids
        }
        episode_ids = whitelisted_episode_ids | exclusion_episode_ids
    else:
        season_ids = set[UUID]()
        episode_ids = blacklisted_episode_ids | result_episode_ids

    existing_channel_show.is_whitelist = result.is_whitelist
    _merge_filters(session, existing_channel_show, season_ids, episode_ids)


def _season_ids_for_episodes(
    session: Session,
    episode_ids: set[UUID],
) -> dict[UUID, UUID]:
    """Map each episode id to its season id."""
    if not episode_ids:
        return {}
    rows = session.exec(
        select(Episode.id, Episode.season_id).where(col(Episode.id).in_(episode_ids)),
    ).all()
    return dict(rows)


def _merge_filters(
    session: Session,
    channel_show: ChannelShow,
    season_ids: set[UUID],
    episode_ids: set[UUID],
) -> None:
    """Merge the given season/episode filters into the channel show's existing ones.

    Existing filters are kept; only values not already present are added, so importing
    never drops filters a previous import or the user already set.
    """
    existing_season_ids = {
        season_filter.season_id for season_filter in channel_show.season_filters
    }
    existing_episode_ids = {
        episode_filter.episode_id for episode_filter in channel_show.episode_filters
    }
    for season_id in season_ids - existing_season_ids:
        session.add(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season_id,
            ),
        )
    for episode_id in episode_ids - existing_episode_ids:
        session.add(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_id=episode_id,
            ),
        )


if __name__ == "__main__":
    configure_logging()
    import_models()
    with Session(engine) as import_session:
        import_queue(import_session)
