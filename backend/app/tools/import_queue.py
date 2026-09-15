# TODO: Validate

import threading
import traceback
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID

from loguru import logger
from sqlmodel import Session, col, or_, select
from tqdm import tqdm

from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelQueue,
    ChannelSeasonFilter,
    ChannelTitle,
    URLStatus,
)
from app.database import engine, load_models
from app.episodes.models import Episode
from app.log import configure_logging
from app.seasons.models import Season
from app.titles.models import Title, TitleTmdbTitle
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.seasons import season_ids_by_key
from app.tmdb_media.service.identifiers import (
    tmdb_record_ids_by_key,
    tmdb_title_ids_by_key,
)
from app.tools.selection import (
    PluginSelection,
    parse_selection,
    selection_description,
)
from app.users.models import User
from app.users.plugin_user import is_plugin_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.manage_plugins import sorted_plugins

logger = logger.bind(source="import_queue")

PLUGIN_LOCKS = {
    plugin_class.plugin_name(): threading.Lock() for plugin_class in sorted_plugins()
}


# TODO: Validate
def run_forever(
    stop_event: threading.Event | None = None,
    *,
    skip_plugin_user_channels: bool = False,
    selection: PluginSelection | None = None,
) -> None:
    stop_event = stop_event or threading.Event()
    while not stop_event.is_set():
        with Session(engine) as session:
            import_queue(
                session,
                skip_plugin_user_channels=skip_plugin_user_channels,
                selection=selection,
            )
        if stop_event.wait(timeout=60):
            break


# TODO: Validate
def import_queue(
    session: Session,
    *,
    skip_plugin_user_channels: bool = False,
    selection: PluginSelection | None = None,
) -> None:
    """Actually import the queue in separate threads for each plugin."""
    grouped = _group_pending_urls_by_plugin(
        session,
        skip_plugin_user_channels=skip_plugin_user_channels,
        selection=selection or PluginSelection(),
    )
    total = sum(len(items) for _, items in grouped)
    if not total:
        return
    with tqdm(total=total, unit="url") as progress:
        for plugin_class, items in grouped:
            plugin_key = plugin_class.plugin_name()
            with PLUGIN_LOCKS[plugin_key]:
                for item in items:
                    progress.set_description(f"[{plugin_key}] {item.url}")
                    _import_one(session, item, plugin_class)
                    progress.update()


# TODO: Validate
def _get_plugin(
    url: str,
    plugin_key: str | None = None,
) -> type[AbstractPlugin] | None:
    # `sorted_plugins` rather than the registry itself, which is only filled in
    # once something has imported the plugins. Nothing here can count on that
    # having happened: the queue is worked by a job that need never have served a
    # request, and an empty registry would fail every URL as unmatched.
    for plugin_class in sorted_plugins():
        # A plugin that imports no URL carries no pattern to match one against.
        if not plugin_class.implements("validate_and_import_url"):
            continue
        if plugin_key is not None and plugin_class.plugin_name() != plugin_key:
            continue
        if plugin_class.is_valid_url_format(url):
            return plugin_class
    return None


# TODO: Validate
def _group_pending_urls_by_plugin(
    session: Session,
    *,
    skip_plugin_user_channels: bool = False,
    selection: PluginSelection | None = None,
) -> list[tuple[type[AbstractPlugin], list[ChannelQueue]]]:
    by_plugin: list[tuple[type[AbstractPlugin], list[ChannelQueue]]] = []
    unmatched: list[ChannelQueue] = []
    selector = (
        select(ChannelQueue)
        .join(Channel, col(ChannelQueue.channel_id) == col(Channel.id))
        .join(User, col(Channel.user_id) == col(User.id))
        .where(
            col(ChannelQueue.status).in_([URLStatus.PENDING, URLStatus.IMPORTING]),
            or_(
                col(ChannelQueue.import_at).is_(None),
                col(ChannelQueue.import_at) <= tz_datetime.now(),
            ),
        )
    )
    if skip_plugin_user_channels:
        selector = selector.where(~is_plugin_user(User.email))
    pending = session.exec(
        selector.order_by(
            is_plugin_user(User.email).asc(),
            col(ChannelQueue.created_at).asc(),
        ),
    ).all()
    plugin_key = (selection or PluginSelection()).plugin_key
    for item in pending:
        if plugin_class := _get_plugin(item.url, plugin_key):
            if by_plugin and by_plugin[-1][0] is plugin_class:
                by_plugin[-1][1].append(item)
            else:
                by_plugin.append((plugin_class, [item]))
        elif plugin_key is None and item.status == URLStatus.PENDING:
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
    plugin_key = plugin_class.plugin_name()
    logger.info(f"[{plugin_key}] Importing URL: {queue_item.url}")
    try:
        queue_item.status = URLStatus.IMPORTING
        plugin_instance = plugin_class(session)
        import_results = plugin_instance.validate_and_import_url(queue_item.url)
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
            plugin_class(session).on_import_url_failure(
                queue_item,
                error,
            )
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
    canonical = _tmdb_record_ids_from_results(session, results)
    existing_channel_titles = {title.tmdb_title_id: title for title in channel.titles}
    for result in results:
        tmdb_title_ids = canonical.titles.get(result.title.key, set())
        if not tmdb_title_ids:
            logger.warning(
                "No canonical title for {}, leaving it off the channel",
                result.title.key,
            )
            continue
        for tmdb_title_id in tmdb_title_ids:
            seasons = canonical.seasons_under(result.season_keys, tmdb_title_id)
            episodes = canonical.episodes_under(result.episode_keys, tmdb_title_id)
            if result.is_whitelist and not seasons and not episodes:
                continue
            existing_channel_title = existing_channel_titles.get(tmdb_title_id)
            if existing_channel_title is None:
                existing_channel_titles[tmdb_title_id] = _create_channel_title(
                    channel,
                    result,
                    tmdb_title_id,
                    seasons,
                    episodes,
                )
            elif existing_channel_title.is_blacklist_only:
                _reset_channel_title(
                    session,
                    existing_channel_title,
                    result,
                    seasons,
                    episodes,
                )
            else:
                _grant_on_channel_title(
                    session,
                    existing_channel_title,
                    result,
                    seasons,
                    episodes,
                )


# TODO: Validate
@dataclass
class _TmdbRecordIds:
    """What each record key in a batch of results resolves to, at every level.

    A title key resolves to every title that listing is linked to, since a listing
    that mixes titles is linked to each of them. A season or an episode key
    resolves to the one row it is, along with the title that row is under, which
    is what says which of a mixed listing's titles it belongs to.
    """

    titles: dict[str, set[UUID]]
    seasons: dict[str, UUID]
    episodes: dict[str, UUID]
    title_by_season: dict[UUID, set[UUID]]
    title_by_episode: dict[UUID, set[UUID]]

    # TODO: Validate
    def seasons_under(
        self,
        season_keys: Collection[str],
        tmdb_title_id: UUID,
    ) -> set[UUID]:
        """Return the seasons `season_keys` name that belong to `tmdb_title_id`."""
        return {
            tmdb_record_id
            for key in season_keys
            if (tmdb_record_id := self.seasons.get(key)) is not None
            and tmdb_title_id in self.title_by_season.get(tmdb_record_id, set())
        }

    # TODO: Validate
    def episodes_under(
        self,
        episode_keys: Collection[str],
        tmdb_title_id: UUID,
    ) -> set[UUID]:
        """Return the episodes `episode_keys` name that belong to `tmdb_title_id`."""
        return {
            tmdb_record_id
            for key in episode_keys
            if (tmdb_record_id := self.episodes.get(key)) is not None
            and tmdb_title_id in self.title_by_episode.get(tmdb_record_id, set())
        }


# TODO: Validate
def _tmdb_record_ids_from_results(
    session: Session,
    results: list[URLImportResult],
) -> _TmdbRecordIds:
    """Resolve every record key the results name, in one query per level."""
    seasons = season_ids_by_key(
        session,
        {key for result in results for key in result.season_keys},
    )
    episodes = tmdb_record_ids_by_key(
        session,
        {key for result in results for key in result.episode_keys},
    )
    return _TmdbRecordIds(
        titles=tmdb_title_ids_by_key(
            session,
            {result.title.key for result in results},
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
    if not season_ids:
        return {}
    titles: dict[UUID, set[UUID]] = defaultdict(set)
    own_rows = session.exec(
        select(  # type: ignore[call-overload]
            Season.id,
            Title.id,
        )
        .join(Title, col(Season.title_id) == col(Title.id))
        .where(col(Season.id).in_(season_ids), is_not_linked(Title)),
    ).all()
    for season_id, tmdb_title_id in own_rows:
        titles[season_id].add(tmdb_title_id)
    linked_rows = session.exec(
        select(  # type: ignore[call-overload]
            Season.id,
            TitleTmdbTitle.tmdb_title_id,
        )
        .join(Title, col(Season.title_id) == col(Title.id))
        .join(TitleTmdbTitle, col(TitleTmdbTitle.title_id) == col(Title.id))
        .where(col(Season.id).in_(season_ids)),
    ).all()
    for season_id, tmdb_title_id in linked_rows:
        titles[season_id].add(tmdb_title_id)
    return titles


# TODO: Validate
def _titles_by_episode(
    session: Session,
    tmdb_episode_ids: set[UUID],
) -> dict[UUID, set[UUID]]:
    if not tmdb_episode_ids:
        return {}
    titles: dict[UUID, set[UUID]] = defaultdict(set)
    own_rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            Title.id,
        )
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Title, col(Season.title_id) == col(Title.id))
        .where(col(Episode.id).in_(tmdb_episode_ids), is_not_linked(Title)),
    ).all()
    for tmdb_episode_id, tmdb_title_id in own_rows:
        titles[tmdb_episode_id].add(tmdb_title_id)
    linked_rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            TitleTmdbTitle.tmdb_title_id,
        )
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Title, col(Season.title_id) == col(Title.id))
        .join(TitleTmdbTitle, col(TitleTmdbTitle.title_id) == col(Title.id))
        .where(col(Episode.id).in_(tmdb_episode_ids)),
    ).all()
    for tmdb_episode_id, tmdb_title_id in linked_rows:
        titles[tmdb_episode_id].add(tmdb_title_id)
    return titles


# TODO: Validate
def _create_channel_title(
    channel: Channel,
    result: URLImportResult,
    tmdb_title_id: UUID,
    season_ids: set[UUID],
    tmdb_episode_ids: set[UUID],
) -> ChannelTitle:
    """Put the title on the channel, with the filters the result asked for."""
    channel_title = ChannelTitle(
        channel_id=channel.id,
        tmdb_title_id=tmdb_title_id,
        is_whitelist=result.is_whitelist,
        is_blacklist_only=False,
    )
    channel.titles.append(channel_title)
    _merge_filters(channel_title, season_ids, tmdb_episode_ids)
    return channel_title


# TODO: Validate
def _reset_channel_title(
    session: Session,
    channel_title: ChannelTitle,
    result: URLImportResult,
    season_ids: set[UUID],
    tmdb_episode_ids: set[UUID],
) -> None:
    channel_title.is_blacklist_only = False
    channel_title.is_whitelist = result.is_whitelist
    _drop_filters(session, channel_title, season_ids, tmdb_episode_ids)
    _merge_filters(channel_title, season_ids, tmdb_episode_ids)


# TODO: Validate
def _grant_on_channel_title(
    session: Session,
    channel_title: ChannelTitle,
    result: URLImportResult,
    season_ids: set[UUID],
    tmdb_episode_ids: set[UUID],
) -> None:
    channel_title.is_blacklist_only = False

    if not result.season_keys and not result.episode_keys:
        if channel_title.is_whitelist:
            channel_title.is_whitelist = False
            _drop_filters(session, channel_title, set(), set())
        return

    filtered_seasons = {
        season_filter.season_id for season_filter in channel_title.season_filters
    }
    filtered_episodes = {
        episode_filter.tmdb_episode_id
        for episode_filter in channel_title.episode_filters
    }
    season_by_episode = _seasons_from_episodes(
        session,
        filtered_episodes | tmdb_episode_ids,
    )

    if channel_title.is_whitelist:
        filtered_seasons |= season_ids
    else:
        filtered_seasons -= season_ids
    filtered_episodes -= {
        tmdb_episode_id
        for tmdb_episode_id in filtered_episodes
        if season_by_episode.get(tmdb_episode_id) in season_ids
    }

    for tmdb_episode_id in tmdb_episode_ids:
        season_is_filtered = season_by_episode.get(tmdb_episode_id) in filtered_seasons
        if season_is_filtered != channel_title.is_whitelist:
            filtered_episodes.add(tmdb_episode_id)
        else:
            filtered_episodes.discard(tmdb_episode_id)

    _drop_filters(session, channel_title, filtered_seasons, filtered_episodes)
    _merge_filters(channel_title, filtered_seasons, filtered_episodes)
    for episode_filter in channel_title.episode_filters:
        if episode_filter.tmdb_episode_id in filtered_episodes:
            episode_filter.expires_at = None


# TODO: Validate
def _seasons_from_episodes(
    session: Session,
    tmdb_episode_ids: set[UUID],
) -> dict[UUID, UUID]:
    if not tmdb_episode_ids:
        return {}
    rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            Episode.season_id,
        ).where(col(Episode.id).in_(tmdb_episode_ids)),
    ).all()
    return dict(rows)


# TODO: Validate
def _drop_filters(
    session: Session,
    channel_title: ChannelTitle,
    season_ids: set[UUID],
    tmdb_episode_ids: set[UUID],
) -> None:
    for season_filter in channel_title.season_filters:
        if season_filter.season_id not in season_ids:
            session.delete(season_filter)
    for episode_filter in channel_title.episode_filters:
        if episode_filter.tmdb_episode_id not in tmdb_episode_ids:
            session.delete(episode_filter)


# TODO: Validate
def _merge_filters(
    channel_title: ChannelTitle,
    season_ids: set[UUID],
    tmdb_episode_ids: set[UUID],
) -> None:
    """Merge the given season/episode filters into the channel title's existing ones.

    Existing filters are kept; only values not already present are added, so importing
    never drops filters a previous import or the user already set.
    """
    existing_seasons = {
        season_filter.season_id for season_filter in channel_title.season_filters
    }
    existing_episodes = {
        episode_filter.tmdb_episode_id
        for episode_filter in channel_title.episode_filters
    }
    for season_id in season_ids - existing_seasons:
        channel_title.season_filters.append(
            ChannelSeasonFilter(
                channel_title_id=channel_title.id,
                season_id=season_id,
            ),
        )
    for tmdb_episode_id in tmdb_episode_ids - existing_episodes:
        channel_title.episode_filters.append(
            ChannelEpisodeFilter(
                channel_title_id=channel_title.id,
                tmdb_episode_id=tmdb_episode_id,
            ),
        )


if __name__ == "__main__":
    selected = parse_selection(
        "Import the queued URLs as they come in.",
        include_source=False,
    )
    configure_logging(lambda message: tqdm.write(message, end=""))
    load_models()
    logger.info(f"Importing the queue for {selection_description(selected)}")
    run_forever(selection=selected)
    logger.info("Import queue process stopped")
