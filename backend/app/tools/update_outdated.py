# TODO: Validate
# pyright: reportArgumentType=false

import time
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar
from tqdm import tqdm

from app.channels.episode_selector.visibility import channel_access_condition
from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelEpisodeSourceFilter,
    ChannelSeasonFilter,
    ChannelSourceFilter,
    ChannelTitle,
)
from app.database import engine, load_models
from app.episodes.models import Episode
from app.log import configure_logging
from app.models import MediaMixin
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle
from app.tmdb_media.episodes import links_of, tmdb_episode_link
from app.users.models import User
from app.users.plugin_user import is_plugin_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
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
    outer: Any,  # noqa: ANN401 - The model the clause is asked about.
    condition: Callable[[Any], ColumnElement[bool]] | None = None,
) -> ColumnElement[bool]:
    """EXISTS clause requiring `season` to be included in some channel.

    A channel holds a title rather than one website's non-canonical row of it, and which
    title an episode belongs to is its canonical episode's answer, since a listing that
    mixes titles holds seasons of each of them. An episode that is linked to nothing
    sits where its own listing filed it, under that listing's title.

    `condition` is handed the listing the season is on, which is what ties the
    clause to the row it is being asked about.
    """
    copy_episode = aliased(Episode)
    tmdb_episode = aliased(Episode)
    copy_link = tmdb_episode_link()
    tmdb_season = aliased(Season)
    copy_title = aliased(Title)
    copy_title_link = aliased(TitleTmdbTitle)
    channel_owner = aliased(User)
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
        # another, so the clause holds where any of them is on a channel.
        .outerjoin(
            copy_title_link,
            col(copy_title_link.title_id) == col(copy_title.id),
        )
        # A listing that is linked to nothing is the title itself and answers for
        # itself, the same way an episode standing for nothing is the episode, so
        # a channel naming it names it by its own id and the last fallback is what
        # reaches those rows.
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
    """EXISTS clause matching a Plugin with no Source of its own.

    Every other clause here asks whether anything below a row is in a channel,
    which a plugin holding no media of its own can never answer: it has no
    `Source` for the question to be asked through.
    """
    return ~(select(Source.id).where(col(Source.plugin_id) == col(Plugin.id)).exists())


# TODO: Validate
def _any_channel_holds_a_title_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring some channel to hold some title.

    The stand-in, for a plugin holding no media of its own, for the question the
    other clauses ask. Its rows are what every channel reads a title out of, so
    a channel holding anything at all is a channel its rows are behind.
    """
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
MEDIA_CLASSES_IN_ORDER: tuple[MediaClass, ...] = (
    Plugin,
    Source,
    Title,
    Season,
    Episode,
)


# TODO: Validate
def _restrict_to_media_in_channel[ResultT](
    statement: SelectOfScalar[ResultT],
    media_class: MediaClass,
) -> SelectOfScalar[ResultT]:
    # Skip items that have no Season included in any channel anywhere below them
    # in the Plugin -> Source -> Title -> Season tree, so unused media is not updated.
    if media_class is Plugin:
        return statement.where(
            _plugin_has_season_in_channel_exists()
            | (_plugin_holds_no_media_exists() & _any_channel_holds_a_title_exists()),
        )
    if media_class is Source:
        return statement.where(_source_has_season_in_channel_exists())
    if media_class is Title:
        return statement.where(_title_has_season_in_channel_exists())
    if media_class in (Season, Episode):
        return statement.where(_season_in_channel_exists())
    return statement


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
def _grouped_by_title[ItemT: MediaMixin[Any]](
    items: Sequence[ItemT],
) -> list[list[ItemT]]:
    """Gather `items` into runs of one title, in the order the titles first appear.

    A plugin reads a title's files once and answers every item of that title out of
    what it read, so the items of one title are handed to one view of the plugin
    rather than to one view each. Ordering is only permuted within a title, never
    across them, so the oldest title is still updated first.
    """
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
def _process_outdated_items(
    session: Session,
    media_class: MediaClass,
    plugin_key: str,
    plugin_class: type[AbstractPlugin],
) -> None:
    media_type_name = media_class.__name__.lower()
    update_method_name = f"update_{media_type_name}"

    statement = (
        media_class.select_with_plugin()
        .where(
            col(media_class.update_at).is_not(None),
            col(media_class.update_at) < tz_datetime.now(),
            col(media_class.deleted_at).is_(None),
        )
        .order_by(col(media_class.update_at).asc())
    )
    # Only this plugin's media so each plugin's run is independent.
    statement = statement.where(col(Plugin.key) == plugin_key)
    statement = _restrict_to_media_in_channel(statement, media_class)

    outdated_items = session.exec(statement).all()
    if not outdated_items:
        return

    log_msg = f"[{plugin_key}] Found {len(outdated_items)} outdated {media_type_name}"
    logger.info(log_msg)

    updated_count = 0
    plugin_record = Plugin.get_one(session, plugin_key)
    progress = tqdm(total=len(outdated_items), unit=media_type_name)
    for group in _grouped_by_title(outdated_items):
        # One view of the plugin per title, so what it read for the title answers
        # every item of it and is let go when the title is done with.
        plugin_instance = plugin_class(session, plugin_record)
        for item in group:
            log_msg = f"[{plugin_key}] Updating {media_type_name}: {item.key}"
            logger.info(log_msg)
            progress.set_description(f"[{plugin_key}] {item.key}")
            progress.update()
            try:
                update = getattr(plugin_instance, update_method_name)
                if media_class is Source:
                    update(item, item.update_at)
                else:
                    update(item)

                log_msg = (
                    f"[{plugin_key}] Successfully updated {media_type_name}: {item.key}"
                )
                logger.info(log_msg)
                updated_count += 1

                session.commit()
            except Exception as error:
                log_msg = (
                    f"[{plugin_key}] Failed to update {media_type_name}: {item.key}"
                )
                logger.exception(log_msg)
                # Roll back partial changes, then let the plugin decide how to
                # reschedule the failed item.
                session.rollback()
                session.refresh(item)
                failure_method_name = f"on_update_{media_type_name}_failure"
                try:
                    getattr(plugin_instance, failure_method_name)(item, error)
                except Exception:  # noqa: BLE001 - The plugin re-raised its default.
                    # Set update_at to the maximum possible value to avoid retrying
                    # the update until the issue is resolved.
                    item.update_at = tz_datetime.max()
                session.commit()
    progress.close()

    log_msg = (
        f"[{plugin_key}] Updated {updated_count} out of {len(outdated_items)} "
        f"outdated {media_type_name}"
    )
    logger.info(log_msg)


# TODO: Validate
def _update_plugin(
    plugin_key: str,
    plugin_class: type[AbstractPlugin],
) -> None:
    """Run the full update sequence for a single plugin in its own session."""
    log_msg = f"[{plugin_key}] Starting update run"
    logger.info(log_msg)
    with Session(engine) as session:
        for media_class in MEDIA_CLASSES_IN_ORDER:
            _process_outdated_items(
                session,
                media_class,
                plugin_key,
                plugin_class,
            )
    log_msg = f"[{plugin_key}] Finished update run"
    logger.info(log_msg)


# TODO: Validate
def _installed_plugin_keys() -> list[str]:
    """Return the keys of every `Plugin` in the database."""
    with Session(engine) as session:
        return list(session.exec(select(Plugin.key)).all())


# TODO: Validate
def _specialized_plugin_keys() -> set[str]:
    """Return the keys of the plugins that have an update run of their own."""
    return {plugin.plugin_name() for plugin in plugins if plugin.specialized_updater()}


# TODO: Validate
def _next_update_at(session: Session) -> datetime | None:
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
                    col(media_class.deleted_at).is_(None),
                    col(Plugin.key).not_in(specialized_keys),
                ),
                media_class,
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
def _seconds_until_next_update() -> float:
    with Session(engine) as session:
        next_update_at = _next_update_at(session)
    if next_update_at is None:
        return MAX_SLEEP_SECONDS
    seconds_until_due = (next_update_at - tz_datetime.now()).total_seconds()
    return max(0.0, min(seconds_until_due, MAX_SLEEP_SECONDS))


# TODO: Validate
def update_outdated() -> None:
    """Update all outdated entries."""
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    specialized_keys = _specialized_plugin_keys()

    for plugin_key in _installed_plugin_keys():
        plugin_class = plugin_classes_by_key.get(plugin_key)
        if plugin_class is None:
            log_msg = f"[{plugin_key}] No installed plugin matches this database entry"
            logger.error(log_msg)
            continue
        # A plugin whose media is updated better by a run of its own is left to it.
        if plugin_key in specialized_keys:
            continue
        try:
            _update_plugin(plugin_key, plugin_class)
        except Exception:
            # Log the plugin-level failure and let the other plugins finish.
            log_msg = f"[{plugin_key}] Plugin update run crashed"
            logger.exception(log_msg)


# TODO: Validate
def _update_outdated_forever() -> None:
    while True:
        update_outdated()
        wait_seconds = _seconds_until_next_update()
        log_msg = f"Next update due in {wait_seconds:.0f}s; waiting"
        logger.info(log_msg)
        time.sleep(wait_seconds)


if __name__ == "__main__":
    configure_logging(lambda message: tqdm.write(message, end=""))
    _update_outdated_forever()
