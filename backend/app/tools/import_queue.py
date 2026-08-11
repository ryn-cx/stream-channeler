# TODO: Validate

import threading
import traceback
from dataclasses import dataclass
from uuid import UUID

from loguru import logger
from sqlmodel import Session, col, or_, select

from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_media.service import canonical_ids_by_key
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
from app.shows.models import Show
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


# TODO: Validate
def run_forever(stop_event: threading.Event | None = None) -> None:  # noqa: D103
    stop_event = stop_event or threading.Event()
    while not stop_event.is_set():
        with Session(engine) as session:
            import_queue(session)
        if stop_event.wait(timeout=60):
            break


# TODO: Validate
def import_queue(session: Session) -> None:
    """Actually import the queue in separate threads for each plugin."""
    for plugin_class, items in _group_pending_urls_by_plugin(session).items():
        with PLUGIN_LOCKS[plugin_class.plugin_key()]:
            for item in items:
                _import_one(session, item, plugin_class)


# TODO: Validate
def _get_plugin(url: str) -> type[AbstractPlugin] | None:
    for plugin_class in plugins:
        if plugin_class.is_valid_url_format(url):
            return plugin_class
    return None


# TODO: Validate
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


# TODO: Validate
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


# TODO: Validate
def add_results_to_channel(
    session: Session,
    results: list[URLImportResult],
    channel: Channel,
) -> None:
    """Add the given import results to the channel.

    A plugin says what a URL imported by the keys of the records it just wrote.
    A channel holds the media itself, so each key is resolved to the row that
    record is a copy of first, and a result naming a record that reached no
    canonical row is left for a later run.
    """
    canonical = _canonical_ids_for_results(session, results)
    existing_channel_shows = {show.canonical_show_id: show for show in channel.shows}
    for result in results:
        canonical_show_id = canonical.shows.get(result.show_key)
        if canonical_show_id is None:
            logger.warning(
                "No canonical title for {}, leaving it off the channel",
                result.show_key,
            )
            continue
        if existing_channel_show := existing_channel_shows.get(canonical_show_id):
            _update_channel_show(session, existing_channel_show, result, canonical)
        else:
            existing_channel_shows[canonical_show_id] = _create_channel_show(
                channel,
                result,
                canonical_show_id,
                canonical,
            )


# TODO: Validate
@dataclass
class _CanonicalIds:
    """What each record key in a batch of results resolves to, at every level."""

    shows: dict[str, UUID]
    seasons: dict[str, UUID]
    episodes: dict[str, UUID]


# TODO: Validate
def _canonical_ids_for_results(
    session: Session,
    results: list[URLImportResult],
) -> _CanonicalIds:
    """Resolve every record key the results name, in one query per level."""
    return _CanonicalIds(
        shows=canonical_ids_by_key(
            session,
            {result.show_key for result in results},
            Show,
        ),
        seasons=canonical_ids_by_key(
            session,
            {key for result in results for key in result.season_keys},
            Season,
        ),
        episodes=canonical_ids_by_key(
            session,
            {key for result in results for key in result.episode_keys},
            Episode,
        ),
    )


# TODO: Validate
def _create_channel_show(
    channel: Channel,
    result: URLImportResult,
    canonical_show_id: UUID,
    canonical: _CanonicalIds,
) -> ChannelShow:
    """Put the title on the channel, with the filters the result asked for."""
    channel_show = ChannelShow(
        channel_id=channel.id,
        canonical_show_id=canonical_show_id,
        is_whitelist=result.is_whitelist,
        is_blacklist_only=False,
    )
    channel.shows.append(channel_show)
    _merge_filters(
        channel_show,
        _resolved(result.season_keys, canonical.seasons),
        _resolved(result.episode_keys, canonical.episodes),
    )
    return channel_show


# TODO: Validate
def _resolved(keys, mapping: dict[str, UUID]) -> set[UUID]:  # noqa: ANN001
    """The canonical rows `keys` name, skipping the ones that name none."""
    return {mapping[key] for key in keys if key in mapping}


# TODO: Validate
def _update_channel_show(
    session: Session,
    existing_channel_show: ChannelShow,
    result: URLImportResult,
    canonical: _CanonicalIds,
) -> None:
    """Fold what the result asks for into the filters the title already carries."""
    existing_channel_show.is_blacklist_only = False

    was_whitelist = existing_channel_show.is_whitelist
    existing_seasons: set[UUID] = {
        season_filter.canonical_season_id
        for season_filter in existing_channel_show.season_filters
    }
    existing_episodes: set[UUID] = {
        episode_filter.canonical_episode_id
        for episode_filter in existing_channel_show.episode_filters
    }
    blacklisted_episodes: set[UUID] = set() if was_whitelist else existing_episodes

    result_seasons = _resolved(result.season_keys, canonical.seasons)
    result_episodes = _resolved(result.episode_keys, canonical.episodes)

    if result.is_whitelist:
        seasons = (existing_seasons if was_whitelist else set[UUID]()) | result_seasons
        whitelisted_episodes = (
            (existing_episodes if was_whitelist else set[UUID]()) | result_episodes
        ) - blacklisted_episodes
        season_by_blacklisted_episode = _seasons_for_episodes(
            session,
            blacklisted_episodes,
        )
        exclusions = {
            canonical_episode_id
            for canonical_episode_id, canonical_season_id in (
                season_by_blacklisted_episode.items()
            )
            if canonical_season_id in seasons
        }
        episodes = whitelisted_episodes | exclusions
    else:
        seasons = set[UUID]()
        episodes = blacklisted_episodes | result_episodes

    existing_channel_show.is_whitelist = result.is_whitelist
    _merge_filters(existing_channel_show, seasons, episodes)


# TODO: Validate
def _seasons_for_episodes(
    session: Session,
    canonical_episode_ids: set[UUID],
) -> dict[UUID, UUID]:
    """Map each canonical episode to the canonical season holding it."""
    if not canonical_episode_ids:
        return {}
    rows = session.exec(
        select(  # type: ignore[call-overload]
            CanonicalEpisode.id,
            CanonicalEpisode.canonical_season_id,
        ).where(col(CanonicalEpisode.id).in_(canonical_episode_ids)),
    ).all()
    return dict(rows)


# TODO: Validate
def _merge_filters(
    channel_show: ChannelShow,
    canonical_season_ids: set[UUID],
    canonical_episode_ids: set[UUID],
) -> None:
    """Merge the given season/episode filters into the channel show's existing ones.

    Existing filters are kept; only values not already present are added, so importing
    never drops filters a previous import or the user already set.
    """
    existing_seasons = {
        season_filter.canonical_season_id
        for season_filter in channel_show.season_filters
    }
    existing_episodes = {
        episode_filter.canonical_episode_id
        for episode_filter in channel_show.episode_filters
    }
    for canonical_season_id in canonical_season_ids - existing_seasons:
        channel_show.season_filters.append(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                canonical_season_id=canonical_season_id,
            ),
        )
    for canonical_episode_id in canonical_episode_ids - existing_episodes:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                canonical_episode_id=canonical_episode_id,
            ),
        )


if __name__ == "__main__":
    configure_logging()
    load_models()
    run_forever()
    logger.info("Import queue process stopped")
