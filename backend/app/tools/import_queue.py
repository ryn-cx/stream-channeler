# TODO: Validate

import threading
import traceback

from loguru import logger
from sqlmodel import Session, col, or_, select

from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelQueue,
    ChannelSeasonFilter,
    ChannelShow,
    URLStatus,
)
from app.database import engine, load_models
from app.episodes.models import Episode
from app.log import configure_logging
from app.seasons.models import Season
from app.utils import tz_datetime
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
        .where(
            col(ChannelQueue.status).in_([URLStatus.PENDING, URLStatus.IMPORTING]),
            or_(
                col(ChannelQueue.import_at).is_(None),
                col(ChannelQueue.import_at) <= tz_datetime.now(),
            ),
        )
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
    except InvalidURLError as error:
        logger.warning(f"[{plugin_key}] Invalid URL: {queue_item.url}")
        queue_item.status = URLStatus.FAILED
        # The plugin explains why the URL cannot be imported, which is the only place
        # the user is told what to do instead.
        queue_item.note = str(error) or "Invalid URL."
        session.commit()
    except Exception as error:
        logger.exception(f"[{plugin_key}] Error importing: {queue_item.url}")
        # Roll back partial changes, then let the plugin decide how to reschedule
        # the failed URL.
        session.rollback()
        session.refresh(queue_item)
        try:
            plugin_class(session).on_import_url_failure(queue_item, error)
        except Exception:  # noqa: BLE001 - The plugin re-raised its default.
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
    existing_channel_shows = {show.show_identifier: show for show in channel.shows}
    for result in results:
        if existing_channel_show := existing_channel_shows.get(
            result.show.show_identifier,
        ):
            _update_channel_show(session, existing_channel_show, result)
        else:
            existing_channel_shows[result.show.show_identifier] = _create_channel_show(
                channel,
                result,
            )


def _create_channel_show(
    channel: Channel,
    result: URLImportResult,
) -> ChannelShow:
    channel_show = ChannelShow(
        channel_id=channel.id,
        show_identifier=result.show.show_identifier,
        is_whitelist=result.is_whitelist,
        is_blacklist_only=False,
    )
    channel.shows.append(channel_show)

    for season in result.seasons:
        channel_show.season_filters.append(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_identifier=season.season_identifier,
            ),
        )

    for episode in result.episodes:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_identifier=episode.episode_identifier,
            ),
        )

    return channel_show


def _update_channel_show(
    session: Session,
    existing_channel_show: ChannelShow,
    result: URLImportResult,
) -> None:
    existing_channel_show.is_blacklist_only = False

    was_whitelist = existing_channel_show.is_whitelist
    existing_seasons: set[str] = {
        season_filter.season_identifier
        for season_filter in existing_channel_show.season_filters
    }
    existing_episodes: set[str] = {
        episode_filter.episode_identifier
        for episode_filter in existing_channel_show.episode_filters
    }
    blacklisted_episodes: set[str] = set() if was_whitelist else existing_episodes

    result_seasons: set[str] = {season.season_identifier for season in result.seasons}
    result_episodes: set[str] = {
        episode.episode_identifier for episode in result.episodes
    }

    if result.is_whitelist:
        seasons = (existing_seasons if was_whitelist else set[str]()) | result_seasons
        whitelisted_episodes = (
            (existing_episodes if was_whitelist else set[str]()) | result_episodes
        ) - blacklisted_episodes
        season_by_blacklisted_episode = _season_identifiers_for_episodes(
            session,
            blacklisted_episodes,
        )
        exclusions = {
            episode_identifier
            for episode_identifier, season_identifier in (
                season_by_blacklisted_episode.items()
            )
            if season_identifier in seasons
        }
        episodes = whitelisted_episodes | exclusions
    else:
        seasons = set[str]()
        episodes = blacklisted_episodes | result_episodes

    existing_channel_show.is_whitelist = result.is_whitelist
    _merge_filters(existing_channel_show, seasons, episodes)


def _season_identifiers_for_episodes(
    session: Session,
    episode_identifiers: set[str],
) -> dict[str, str]:
    """Map each episode identifier to the identifier of the season holding it."""
    if not episode_identifiers:
        return {}
    rows = session.exec(
        select(Episode.episode_identifier, Season.season_identifier)  # type: ignore[call-overload]
        .join(Season, col(Season.id) == col(Episode.season_id))
        .where(col(Episode.episode_identifier).in_(episode_identifiers)),
    ).all()
    return dict(rows)


def _merge_filters(
    channel_show: ChannelShow,
    season_identifiers: set[str],
    episode_identifiers: set[str],
) -> None:
    """Merge the given season/episode filters into the channel show's existing ones.

    Existing filters are kept; only values not already present are added, so importing
    never drops filters a previous import or the user already set.
    """
    existing_seasons = {
        season_filter.season_identifier for season_filter in channel_show.season_filters
    }
    existing_episodes = {
        episode_filter.episode_identifier
        for episode_filter in channel_show.episode_filters
    }
    for season_identifier in season_identifiers - existing_seasons:
        channel_show.season_filters.append(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_identifier=season_identifier,
            ),
        )
    for episode_identifier in episode_identifiers - existing_episodes:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_identifier=episode_identifier,
            ),
        )


if __name__ == "__main__":
    configure_logging()
    load_models()
    with Session(engine) as import_session:
        import_queue(import_session)
