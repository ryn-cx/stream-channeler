# TODO: Validate
# pyright: reportArgumentType=false

import time
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.channels.episode_selector.visibility import channel_access_condition
from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelEpisodeSourceFilter,
    ChannelOrderGroupFilter,
    ChannelSeasonFilter,
    ChannelSourceFilter,
    ChannelTitle,
)
from app.database import engine, load_models
from app.episodes.models import Episode
from app.files.models import File
from app.log import configure_logging, progress_bar
from app.media.service.updating import update_record
from app.models import MediaMixin
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle
from app.titles.service.linking import link_title
from app.tmdb_media.episodes import links_of, tmdb_episode_link
from app.tmdb_media.models import TmdbEpisodeOrderEntry, TmdbEpisodeOrderGroup
from app.tools.selection import (
    PluginSelection,
    parse_selection,
    selection_clauses,
    selection_description,
)
from app.users.models import User
from app.users.plugin_user import is_plugin_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.constants import OUTDATED_STATUS
from plugins.utils.manage_plugins import (
    import_plugins,
    plugins,
)

logger = logger.bind(source="updater")

import_plugins()
load_models()

# Every media class updated by this script; typed as the shared `MediaMixin` base so
# `select_with_plugin()` resolves to a single return type rather than a union.
MediaClass = type[MediaMixin[Any]]


# TODO: Validate
def _channel_inclusion_clause(
    channel_owner: Any,  # noqa: ANN401 - The `User` alias the channel is joined to.
) -> ColumnElement[bool]:
    return (
        col(ChannelTitle.is_blacklist_only).is_(False)
        & channel_access_condition()
        & ~is_plugin_user(channel_owner.email)
    )


# TODO: Validate
def _channel_season_exists(
    season: Any,  # noqa: ANN401 - A `Season` alias, or `Season` itself when correlated.
    outer: Any,  # noqa: ANN401
    condition: Callable[[Any], ColumnElement[bool]] | None = None,
) -> ColumnElement[bool]:
    copy_episode = aliased(Episode)
    tmdb_episode = aliased(Episode)
    copy_link = tmdb_episode_link()
    tmdb_season = aliased(Season)
    copy_title = aliased(Title)
    copy_title_link = aliased(TitleTmdbTitle)
    channel_owner = aliased(User)
    order_entry = aliased(TmdbEpisodeOrderEntry)
    order_group = aliased(TmdbEpisodeOrderGroup)
    season_id = func.coalesce(
        col(tmdb_episode.season_id),
        col(copy_episode.season_id),
    )
    episode_id = func.coalesce(
        col(copy_link.tmdb_episode_id),
        col(copy_episode.id),
    )
    conditions = [condition(copy_title)] if condition else []
    statement = select(ChannelTitle.id).select_from(copy_episode)
    if season is not outer:
        statement = statement.join(
            season,
            col(copy_episode.season_id) == col(season.id),
        )
    return (
        statement.outerjoin(copy_link, links_of(copy_episode, copy_link))
        .outerjoin(
            tmdb_episode,
            col(copy_link.tmdb_episode_id) == col(tmdb_episode.id),
        )
        .outerjoin(
            tmdb_season,
            col(tmdb_episode.season_id) == col(tmdb_season.id),
        )
        .join(copy_title, col(copy_title.id) == col(season.title_id))
        # An episode with no canonical row of its own belongs to every title its listing
        # is linked to, since a listing is no more a non-canonical row of one than of
        .outerjoin(
            copy_title_link,
            col(copy_title_link.title_id) == col(copy_title.id),
        )
        .join(
            ChannelTitle,
            col(ChannelTitle.tmdb_title_id)
            == func.coalesce(
                col(tmdb_season.title_id),
                col(copy_title_link.tmdb_title_id),
                col(copy_title.id),
            ),
        )
        .join(Channel, col(Channel.id) == col(ChannelTitle.channel_id))
        .join(channel_owner, col(Channel.user_id) == col(channel_owner.id))
        .outerjoin(
            ChannelSeasonFilter,
            (col(ChannelSeasonFilter.channel_title_id) == col(ChannelTitle.id))
            & (col(ChannelSeasonFilter.season_id) == season_id),
        )
        .outerjoin(
            ChannelSourceFilter,
            and_(
                col(ChannelSourceFilter.channel_title_id) == col(ChannelTitle.id),
                col(ChannelSourceFilter.title_id) == col(copy_title.id),
            ),
        )
        .outerjoin(
            order_entry,
            and_(
                col(order_entry.order_id) == col(ChannelTitle.tmdb_episode_order_id),
                col(order_entry.tmdb_episode_id) == episode_id,
            ),
        )
        .outerjoin(
            order_group,
            col(order_group.id) == col(order_entry.group_id),
        )
        .outerjoin(
            ChannelOrderGroupFilter,
            and_(
                col(ChannelOrderGroupFilter.channel_title_id) == col(ChannelTitle.id),
                col(ChannelOrderGroupFilter.tmdb_episode_order_group_id)
                == col(order_group.id),
            ),
        )
        .outerjoin(
            ChannelEpisodeFilter,
            and_(
                col(ChannelEpisodeFilter.channel_title_id) == col(ChannelTitle.id),
                col(ChannelEpisodeFilter.tmdb_episode_id) == episode_id,
                or_(
                    col(ChannelEpisodeFilter.expires_at).is_(None),
                    col(ChannelEpisodeFilter.expires_at) > tz_datetime.now(),
                ),
            ),
        )
        .outerjoin(
            ChannelEpisodeSourceFilter,
            and_(
                col(ChannelEpisodeSourceFilter.channel_title_id)
                == col(ChannelTitle.id),
                col(ChannelEpisodeSourceFilter.tmdb_episode_id) == episode_id,
                col(ChannelEpisodeSourceFilter.title_id) == col(copy_title.id),
                or_(
                    col(ChannelEpisodeSourceFilter.expires_at).is_(None),
                    col(ChannelEpisodeSourceFilter.expires_at) > tz_datetime.now(),
                ),
            ),
        )
        .where(
            col(copy_episode.season_id) == col(season.id),
            _channel_inclusion_clause(channel_owner),
            *conditions,
        )
        .correlate(outer)
        .exists()
    )


# TODO: Validate
def _season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Season to be included in some channel."""
    return _channel_season_exists(Season, Season)


# TODO: Validate
def _title_has_season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Title to have a Season included in a channel."""
    season = aliased(Season)
    return _channel_season_exists(
        season,
        Title,
        lambda copy_title: col(copy_title.id) == col(Title.id),
    )


# TODO: Validate
def _source_has_season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Source to have a Season included in a channel."""
    season = aliased(Season)
    return _channel_season_exists(
        season,
        Source,
        lambda copy_title: col(copy_title.source_id) == col(Source.id),
    )


# TODO: Validate
def _plugin_has_season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Plugin to have a Season included in a channel."""
    season = aliased(Season)
    plugin_source = aliased(Source)
    return _channel_season_exists(
        season,
        Plugin,
        lambda copy_title: col(copy_title.source_id).in_(
            select(plugin_source.id)
            .where(col(plugin_source.plugin_id) == col(Plugin.id))
            .correlate(Plugin),
        ),
    )


# TODO: Validate
def _plugin_holds_no_media_exists() -> ColumnElement[bool]:
    plugin_source = aliased(Source)
    return ~(
        select(Title.id)
        .join(plugin_source, col(Title.source_id) == col(plugin_source.id))
        .where(col(plugin_source.plugin_id) == col(Plugin.id))
        .correlate(Plugin)
        .exists()
    )


# TODO: Validate
def _any_channel_holds_a_title_exists() -> ColumnElement[bool]:
    channel_owner = aliased(User)
    return (
        select(ChannelTitle.id)
        .select_from(ChannelTitle)
        .join(Channel, col(Channel.id) == col(ChannelTitle.channel_id))
        .join(channel_owner, col(Channel.user_id) == col(channel_owner.id))
        .where(~is_plugin_user(channel_owner.email))
        .exists()
    )


# Media classes are updated in this order per plugin because updating a plugin can mark
# its own sources outdated, which the Source pass then picks up in
# the same run; the same cascade applies down the Source -> Title -> Season -> Episode
# chain.
CHUNK_SIZE = 100

MEDIA_CLASSES_IN_ORDER: tuple[MediaClass, ...] = (
    Plugin,
    Source,
    File,
    Title,
    Season,
    Episode,
)


# TODO: Validate
def _in_channel_condition(media_class: MediaClass) -> ColumnElement[bool] | None:
    if media_class is Plugin:
        return _plugin_has_season_in_channel_exists() | (
            _plugin_holds_no_media_exists() & _any_channel_holds_a_title_exists()
        )
    if media_class is Source:
        return _source_has_season_in_channel_exists()
    if media_class is Title:
        return _title_has_season_in_channel_exists()
    if media_class in (Season, Episode):
        return _season_in_channel_exists()
    return None


# TODO: Validate
def _restrict_to_media_in_channel[ResultT](
    statement: SelectOfScalar[ResultT],
    media_class: MediaClass,
    *,
    user_channels_only: bool = False,
) -> SelectOfScalar[ResultT]:
    condition = _in_channel_condition(media_class)
    if condition is None:
        return statement
    if user_channels_only:
        return statement.where(condition)
    return statement.where(
        condition
        | (col(media_class.status) == OUTDATED_STATUS)
        | (col(media_class.update_at) < tz_datetime.now() - timedelta(days=365)),
    )


# TODO: Validate
def _title_key(item: MediaMixin[Any]) -> str | None:
    """Return the key of the title `item` belongs to, where it belongs to one."""
    if isinstance(item, Title):
        return item.key
    if isinstance(item, Season):
        return item.title.key
    if isinstance(item, Episode):
        return item.season.title.key
    return None


# TODO: Validate
def _title_of(item: MediaMixin[Any]) -> Title | None:
    """Return the title `item` belongs to, where it belongs to one."""
    if isinstance(item, Title):
        return item
    if isinstance(item, Season):
        return item.title
    if isinstance(item, Episode):
        return item.season.title
    return None


# TODO: Validate
def _link_updated_titles(session: Session, title_ids: Sequence[uuid.UUID]) -> None:
    """Match every title the run updated against TMDB, once the run is over.

    An update is how a new episode arrives, and it arrives standing only for
    itself, so the run that brought it in is the run that decides which TMDB
    episode it is rather than leaving it for whenever the title is relinked next.
    Left until the updates are done because linking imports TMDB's own records
    through a second plugin, and a plugin part way through an update is holding
    records it preloaded that another plugin's import would pull out from under it.
    """
    for title_id in title_ids:
        session.expire_all()
        title = session.exec(
            Title.select_with_plugin().where(Title.id == title_id),
        ).one()
        link_title(session, title)
        session.commit()


# TODO: Validate
def _grouped_by_title[ItemT: MediaMixin[Any]](
    items: Sequence[ItemT],
) -> list[list[ItemT]]:
    groups: list[list[ItemT]] = []
    group_by_title_key: dict[str, list[ItemT]] = {}
    for item in items:
        title_key = _title_key(item)
        if title_key is None:
            groups.append([item])
            continue
        if (group := group_by_title_key.get(title_key)) is None:
            group = []
            group_by_title_key[title_key] = group
            groups.append(group)
        group.append(item)
    return groups


# TODO: Validate
def _outdated_chunk(
    session: Session,
    media_class: MediaClass,
    plugin_key: str,
    processed: set[uuid.UUID],
    selection: PluginSelection,
) -> list[Any]:
    statement = media_class.select_with_plugin().where(
        col(media_class.update_at).is_not(None),
        col(media_class.update_at) < tz_datetime.now(),
    )
    # Only this plugin's media so each plugin's run is independent.
    statement = statement.where(col(Plugin.key) == plugin_key)
    statement = _restrict_to_media_in_channel(
        statement,
        media_class,
        user_channels_only=selection.user_channels_only,
    )

    in_channel = _in_channel_condition(media_class)
    order: list[Any] = [] if in_channel is None else [in_channel.desc()]
    order.append(col(media_class.update_at).asc())
    statement = statement.order_by(*order).limit(CHUNK_SIZE + len(processed))

    items = [item for item in session.exec(statement).all() if item.id not in processed]
    return items[:CHUNK_SIZE]


# TODO: Validate
def _update_outdated_chunk(
    session: Session,
    chunk: list[Any],
    media_class: MediaClass,
    plugin_key: str,
    plugin_class: type[AbstractPlugin],
) -> tuple[int, list[uuid.UUID]]:
    media_type_name = media_class.__name__.lower()
    plugin_record = Plugin.get_one(session, plugin_key)
    updated_title_ids: list[uuid.UUID] = []
    updated_count = 0
    progress = progress_bar(total=len(chunk), unit=media_type_name)
    for group in _grouped_by_title(chunk):
        plugin_instance = plugin_class(session, plugin_record)
        for item in group:
            log_msg = f"[{plugin_key}] Updating {media_type_name}: {item.key}"
            logger.info(log_msg)
            progress.set_description(f"[{plugin_key}] {item.key}")
            progress.update()
            if update_record(session, plugin_instance, plugin_key, item):
                updated_count += 1
        if (title := _title_of(group[0])) is not None:
            updated_title_ids.append(title.id)
    progress.close()
    return updated_count, updated_title_ids


# TODO: Validate
def _process_outdated_items(
    session: Session,
    media_class: MediaClass,
    plugin_key: str,
    plugin_class: type[AbstractPlugin],
    selection: PluginSelection,
) -> None:
    media_type_name = media_class.__name__.lower()
    processed: set[uuid.UUID] = set()
    updated_title_ids: list[uuid.UUID] = []
    updated_count = 0

    while chunk := _outdated_chunk(
        session,
        media_class,
        plugin_key,
        processed,
        selection,
    ):
        log_msg = f"[{plugin_key}] Found {len(chunk)} outdated {media_type_name}"
        logger.info(log_msg)
        processed.update(item.id for item in chunk)
        chunk_updated_count, chunk_title_ids = _update_outdated_chunk(
            session,
            chunk,
            media_class,
            plugin_key,
            plugin_class,
        )
        updated_count += chunk_updated_count
        updated_title_ids += chunk_title_ids

    if not processed:
        return

    _link_updated_titles(session, updated_title_ids)

    log_msg = (
        f"[{plugin_key}] Updated {updated_count} out of {len(processed)} "
        f"outdated {media_type_name}"
    )
    logger.info(log_msg)


# TODO: Validate
def _update_plugin(
    plugin_key: str,
    plugin_class: type[AbstractPlugin],
    selection: PluginSelection,
) -> None:
    """Run the full update sequence for a single plugin in its own session."""
    log_msg = f"[{plugin_key}] Starting update run"
    logger.info(log_msg)
    with Session(engine, expire_on_commit=False) as session:
        for media_class in MEDIA_CLASSES_IN_ORDER:
            if media_class is File and not plugin_class.implements("update_file"):
                continue
            _process_outdated_items(
                session,
                media_class,
                plugin_key,
                plugin_class,
                selection,
            )
    log_msg = f"[{plugin_key}] Finished update run"
    logger.info(log_msg)


# TODO: Validate
def _installed_plugin_keys(selection: PluginSelection) -> list[str]:
    """Return the keys of every `Plugin` in the database."""
    with Session(engine, expire_on_commit=False) as session:
        statement = select(Plugin.key)
        if selection.plugin_keys:
            statement = statement.where(col(Plugin.key).in_(selection.plugin_keys))
        return list(session.exec(statement).all())


# TODO: Validate
def _specialized_plugin_keys() -> set[str]:
    """Return the keys of the plugins that have an update run of their own."""
    return {plugin.plugin_name() for plugin in plugins if plugin.specialized_updater()}


# TODO: Validate
def _next_update_at(session: Session, selection: PluginSelection) -> datetime | None:
    """Return the soonest future `update_at` across the plugin user's media, if any.

    Items already due (`update_at <= now`) are excluded because they are handled by the
    run that just finished; this is only used to decide how long to wait for the next one
    to come due. Media that no channel includes is excluded so the wait is not cut short
    by an item that the update run would skip.
    """
    soonest: datetime | None = None
    specialized_keys = _specialized_plugin_keys()
    for media_class in MEDIA_CLASSES_IN_ORDER:
        statement = (
            _restrict_to_media_in_channel(
                media_class.select_with_plugin().where(
                    col(media_class.update_at) > tz_datetime.now(),
                    col(Plugin.key).not_in(specialized_keys),
                    *selection_clauses(selection),
                ),
                media_class,
                user_channels_only=selection.user_channels_only,
            )
            .order_by(col(media_class.update_at).asc())
            .limit(1)
        )
        item = session.exec(statement).first()
        if (
            item is not None
            and item.update_at is not None
            and (soonest is None or item.update_at < soonest)
        ):
            soonest = item.update_at
    return soonest


# When nothing is scheduled, or the next update is far away, re-check at least once a day
# so externally-added or externally-rescheduled items are still picked up.
MAX_SLEEP_SECONDS = 60.0 * 60.0 * 24.0


# TODO: Validate
def _seconds_until_next_update(selection: PluginSelection) -> float:
    with Session(engine, expire_on_commit=False) as session:
        next_update_at = _next_update_at(session, selection)
    if next_update_at is None:
        return MAX_SLEEP_SECONDS
    seconds_until_due = (next_update_at - tz_datetime.now()).total_seconds()
    return max(0.0, min(seconds_until_due, MAX_SLEEP_SECONDS))


# TODO: Validate
def update_outdated(selection: PluginSelection | None = None) -> None:
    """Update all outdated entries."""
    selection = selection or PluginSelection()
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    specialized_keys = _specialized_plugin_keys()

    for plugin_key in _installed_plugin_keys(selection):
        plugin_class = plugin_classes_by_key.get(plugin_key)
        if plugin_class is None:
            log_msg = f"[{plugin_key}] No installed plugin matches this database entry"
            logger.error(log_msg)
            continue
        # A plugin whose media is updated better by a run of its own is left to it.
        if plugin_key in specialized_keys:
            continue
        try:
            _update_plugin(plugin_key, plugin_class, selection)
        except Exception:
            # Log the plugin-level failure and let the other plugins finish.
            log_msg = f"[{plugin_key}] Plugin update run crashed"
            logger.exception(log_msg)


# TODO: Validate
def _update_outdated_forever(selection: PluginSelection | None = None) -> None:
    selection = selection or PluginSelection()
    while True:
        update_outdated(selection)
        wait_seconds = _seconds_until_next_update(selection)
        log_msg = f"Next update due in {wait_seconds:.0f}s; waiting"
        logger.info(log_msg)
        time.sleep(wait_seconds)


if __name__ == "__main__":
    selected = parse_selection(
        "Update every outdated title, season and episode.",
        include_source=False,
    )

    configure_logging()
    log_msg = f"Updating {selection_description(selected)}"
    logger.info(log_msg)
    _update_outdated_forever(selected)
