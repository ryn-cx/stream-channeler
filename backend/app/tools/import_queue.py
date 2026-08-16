# TODO: Validate

import threading
import traceback
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID

from loguru import logger
from sqlmodel import Session, col, or_, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.seasons import season_ids_by_key
from app.canonical_media.service import (
    canonical_ids_by_key,
    canonical_show_ids_by_key,
)
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
from app.shows.models import Show, ShowCanonicalShow
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
        # A plugin that imports no URL carries no pattern to match one against.
        if not plugin_class.implements("import_url"):
            continue
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

    A listing that mixes titles is a copy of each of them, so it goes on the
    channel as every title it brought in, each holding only the seasons and
    episodes that belong to it. A title the result names nothing of is left off
    when the result is a whitelist, since a whitelist naming none of a title's
    episodes is a title with nothing to offer.
    """
    canonical = _canonical_ids_for_results(session, results)
    existing_channel_shows = {show.canonical_show_id: show for show in channel.shows}
    for result in results:
        canonical_show_ids = canonical.shows.get(result.show_key, set())
        if not canonical_show_ids:
            logger.warning(
                "No canonical title for {}, leaving it off the channel",
                result.show_key,
            )
            continue
        for canonical_show_id in canonical_show_ids:
            seasons = canonical.seasons_under(result.season_keys, canonical_show_id)
            episodes = canonical.episodes_under(result.episode_keys, canonical_show_id)
            if result.is_whitelist and not seasons and not episodes:
                continue
            if existing_channel_show := existing_channel_shows.get(canonical_show_id):
                _update_channel_show(
                    session,
                    existing_channel_show,
                    result,
                    seasons,
                    episodes,
                )
            else:
                existing_channel_shows[canonical_show_id] = _create_channel_show(
                    channel,
                    result,
                    canonical_show_id,
                    seasons,
                    episodes,
                )


# TODO: Validate
@dataclass
class _CanonicalIds:
    """What each record key in a batch of results resolves to, at every level.

    A show key resolves to every title that listing is a copy of, since a listing
    that mixes titles is a copy of each of them. A season or an episode key
    resolves to the one row it is, along with the title that row is under, which
    is what says which of a mixed listing's titles it belongs to.
    """

    shows: dict[str, set[UUID]]
    seasons: dict[str, UUID]
    episodes: dict[str, UUID]
    title_by_season: dict[UUID, set[UUID]]
    title_by_episode: dict[UUID, set[UUID]]

    # TODO: Validate
    def seasons_under(
        self,
        season_keys: Collection[str],
        canonical_show_id: UUID,
    ) -> set[UUID]:
        """The seasons `season_keys` name that belong to `canonical_show_id`."""
        return {
            canonical_id
            for key in season_keys
            if (canonical_id := self.seasons.get(key)) is not None
            and canonical_show_id in self.title_by_season.get(canonical_id, set())
        }

    # TODO: Validate
    def episodes_under(
        self,
        episode_keys: Collection[str],
        canonical_show_id: UUID,
    ) -> set[UUID]:
        """The episodes `episode_keys` name that belong to `canonical_show_id`."""
        return {
            canonical_id
            for key in episode_keys
            if (canonical_id := self.episodes.get(key)) is not None
            and canonical_show_id in self.title_by_episode.get(canonical_id, set())
        }


# TODO: Validate
def _canonical_ids_for_results(
    session: Session,
    results: list[URLImportResult],
) -> _CanonicalIds:
    """Resolve every record key the results name, in one query per level."""
    seasons = season_ids_by_key(
        session,
        {key for result in results for key in result.season_keys},
    )
    episodes = canonical_ids_by_key(
        session,
        {key for result in results for key in result.episode_keys},
    )
    return _CanonicalIds(
        shows=canonical_show_ids_by_key(
            session,
            {result.show_key for result in results},
        ),
        seasons=seasons,
        episodes=episodes,
        title_by_season=_titles_by_season(session, set(seasons.values())),
        title_by_episode=_titles_by_episode(session, set(episodes.values())),
    )


# TODO: Validate
def _titles_by_season(
    session: Session,
    season_ids: set[UUID],
) -> dict[UUID, set[UUID]]:
    """Map each season to the titles holding it.

    A season of a title is held by that title alone. A season a website filed
    under its own listing is held by every title the listing is a copy of, since
    a listing that mixes titles is as much each of them as any other.
    """
    if not season_ids:
        return {}
    titles: dict[UUID, set[UUID]] = defaultdict(set)
    own_rows = session.exec(
        select(  # type: ignore[call-overload]
            Season.id,
            Show.id,
        )
        .join(Show, col(Season.show_id) == col(Show.id))
        .where(col(Season.id).in_(season_ids), is_canonical(Show)),
    ).all()
    for season_id, canonical_show_id in own_rows:
        titles[season_id].add(canonical_show_id)
    linked_rows = session.exec(
        select(  # type: ignore[call-overload]
            Season.id,
            ShowCanonicalShow.canonical_show_id,
        )
        .join(Show, col(Season.show_id) == col(Show.id))
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(Show.id))
        .where(col(Season.id).in_(season_ids)),
    ).all()
    for season_id, canonical_show_id in linked_rows:
        titles[season_id].add(canonical_show_id)
    return titles


# TODO: Validate
def _titles_by_episode(
    session: Session,
    canonical_episode_ids: set[UUID],
) -> dict[UUID, set[UUID]]:
    """Map each canonical episode to the titles holding it.

    An episode of a title is held by that title alone. An episode a website filed
    under its own listing is held by every title the listing is a copy of, since
    a listing that mixes titles is as much each of them as any other.
    """
    if not canonical_episode_ids:
        return {}
    titles: dict[UUID, set[UUID]] = defaultdict(set)
    own_rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            Show.id,
        )
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Show, col(Season.show_id) == col(Show.id))
        .where(col(Episode.id).in_(canonical_episode_ids), is_canonical(Show)),
    ).all()
    for canonical_episode_id, canonical_show_id in own_rows:
        titles[canonical_episode_id].add(canonical_show_id)
    linked_rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            ShowCanonicalShow.canonical_show_id,
        )
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Show, col(Season.show_id) == col(Show.id))
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(Show.id))
        .where(col(Episode.id).in_(canonical_episode_ids)),
    ).all()
    for canonical_episode_id, canonical_show_id in linked_rows:
        titles[canonical_episode_id].add(canonical_show_id)
    return titles


# TODO: Validate
def _create_channel_show(
    channel: Channel,
    result: URLImportResult,
    canonical_show_id: UUID,
    season_ids: set[UUID],
    canonical_episode_ids: set[UUID],
) -> ChannelShow:
    """Put the title on the channel, with the filters the result asked for."""
    channel_show = ChannelShow(
        channel_id=channel.id,
        canonical_show_id=canonical_show_id,
        is_whitelist=result.is_whitelist,
        is_blacklist_only=False,
    )
    channel.shows.append(channel_show)
    _merge_filters(channel_show, season_ids, canonical_episode_ids)
    return channel_show


# TODO: Validate
def _update_channel_show(
    session: Session,
    existing_channel_show: ChannelShow,
    result: URLImportResult,
    result_seasons: set[UUID],
    result_episodes: set[UUID],
) -> None:
    """Fold what the result asks for into the filters the title already carries."""
    existing_channel_show.is_blacklist_only = False

    was_whitelist = existing_channel_show.is_whitelist
    existing_seasons: set[UUID] = {
        season_filter.season_id
        for season_filter in existing_channel_show.season_filters
    }
    existing_episodes: set[UUID] = {
        episode_filter.canonical_episode_id
        for episode_filter in existing_channel_show.episode_filters
    }
    blacklisted_episodes: set[UUID] = set() if was_whitelist else existing_episodes

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
            for canonical_episode_id, season_id in (
                season_by_blacklisted_episode.items()
            )
            if season_id in seasons
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
    """Map each canonical episode to the season holding it."""
    if not canonical_episode_ids:
        return {}
    rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            Episode.season_id,
        ).where(col(Episode.id).in_(canonical_episode_ids)),
    ).all()
    return dict(rows)


# TODO: Validate
def _merge_filters(
    channel_show: ChannelShow,
    season_ids: set[UUID],
    canonical_episode_ids: set[UUID],
) -> None:
    """Merge the given season/episode filters into the channel show's existing ones.

    Existing filters are kept; only values not already present are added, so importing
    never drops filters a previous import or the user already set.
    """
    existing_seasons = {
        season_filter.season_id for season_filter in channel_show.season_filters
    }
    existing_episodes = {
        episode_filter.canonical_episode_id
        for episode_filter in channel_show.episode_filters
    }
    for season_id in season_ids - existing_seasons:
        channel_show.season_filters.append(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season_id,
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
