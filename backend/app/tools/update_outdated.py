# TODO: Validate
# pyright: reportArgumentType=false

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import or_
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.channels.models import ChannelSeasonFilter, ChannelShow
from app.config import settings
from app.database import engine, load_models
from app.episodes.models import Episode
from app.log import configure_logging
from app.models import MediaMixin
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import import_plugins, plugins

logger = logger.bind(source="updater")

import_plugins()
load_models()

# Every media class updated by this script; typed as the shared `MediaMixin` base so
# `select_with_plugin()` resolves to a single return type rather than a union.
MediaClass = type[MediaMixin[Any, Any]]


def _channel_inclusion_clause() -> ColumnElement[bool]:
    return col(ChannelShow.is_blacklist_only).is_(False) & or_(
        col(ChannelShow.is_whitelist).is_(True)
        & col(ChannelSeasonFilter.season_id).is_not(None),
        col(ChannelShow.is_whitelist).is_(False)
        & col(ChannelSeasonFilter.season_id).is_(None),
    )


def _season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Season to be included in some channel."""
    return (
        select(ChannelShow.id)
        .outerjoin(
            ChannelSeasonFilter,
            (col(ChannelSeasonFilter.channel_show_id) == col(ChannelShow.id))
            & (col(ChannelSeasonFilter.season_id) == col(Season.id)),
        )
        .where(
            col(ChannelShow.show_id) == col(Season.show_id),
            _channel_inclusion_clause(),
        )
        .exists()
    )


def _show_has_season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Show to have a Season included in a channel."""
    return (
        select(Season.id)
        .join(ChannelShow, col(ChannelShow.show_id) == col(Season.show_id))
        .outerjoin(
            ChannelSeasonFilter,
            (col(ChannelSeasonFilter.channel_show_id) == col(ChannelShow.id))
            & (col(ChannelSeasonFilter.season_id) == col(Season.id)),
        )
        .where(
            col(Season.show_id) == col(Show.id),
            _channel_inclusion_clause(),
        )
        .exists()
    )


def _source_has_season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Source to have a Season included in a channel."""
    return (
        select(Season.id)
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(ChannelShow, col(ChannelShow.show_id) == col(Season.show_id))
        .outerjoin(
            ChannelSeasonFilter,
            (col(ChannelSeasonFilter.channel_show_id) == col(ChannelShow.id))
            & (col(ChannelSeasonFilter.season_id) == col(Season.id)),
        )
        .where(
            col(Show.source_id) == col(Source.id),
            _channel_inclusion_clause(),
        )
        .exists()
    )


def _plugin_has_season_in_channel_exists() -> ColumnElement[bool]:
    """EXISTS clause requiring the outer Plugin to have a Season included in a channel."""
    return (
        select(Season.id)
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(ChannelShow, col(ChannelShow.show_id) == col(Season.show_id))
        .outerjoin(
            ChannelSeasonFilter,
            (col(ChannelSeasonFilter.channel_show_id) == col(ChannelShow.id))
            & (col(ChannelSeasonFilter.season_id) == col(Season.id)),
        )
        .where(
            col(Source.plugin_id) == col(Plugin.id),
            _channel_inclusion_clause(),
        )
        .exists()
    )


# Media classes are updated in this order per plugin because updating a plugin (e.g.
# JustWatch) can mark its own sources outdated, which the Source pass then picks up in
# the same run; the same cascade applies down the Source -> Show -> Season -> Episode
# chain.
MEDIA_CLASSES_IN_ORDER: tuple[MediaClass, ...] = (
    Plugin,
    Source,
    Show,
    Season,
    Episode,
)


def _restrict_to_plugin_user[ResultT](
    statement: SelectOfScalar[ResultT],
) -> SelectOfScalar[ResultT]:
    return statement.join(User, Plugin.user_id == User.id).where(  # type: ignore[arg-type]
        User.email == PLUGIN_USER_EMAIL,
    )


def _restrict_to_media_in_channel[ResultT](
    statement: SelectOfScalar[ResultT],
    media_class: MediaClass,
) -> SelectOfScalar[ResultT]:
    # Skip items that have no Season included in any channel anywhere below them
    # in the Plugin -> Source -> Show -> Season tree, so unused media is not updated.
    if media_class is Plugin:
        return statement.where(_plugin_has_season_in_channel_exists())
    if media_class is Source:
        return statement.where(_source_has_season_in_channel_exists())
    if media_class is Show:
        return statement.where(_show_has_season_in_channel_exists())
    if media_class in (Season, Episode):
        return statement.where(_season_in_channel_exists())
    return statement


def _process_outdated_items(
    session: Session,
    media_class: MediaClass,
    plugin_key: str,
    plugin_class: type[AbstractPlugin],
    stop_event: threading.Event,
) -> None:
    media_type_name = media_class.__name__.lower()
    update_method_name = f"update_{media_type_name}"

    statement = _restrict_to_plugin_user(
        media_class.select_with_plugin()
        .where(
            col(media_class.update_at).is_not(None),
            col(media_class.update_at) < tz_datetime.now(),
            col(media_class.deleted_at).is_(None),
        )
        .order_by(col(media_class.update_at).asc()),
    )
    # Only this plugin's media so each plugin's run is independent.
    statement = statement.where(col(Plugin.key) == plugin_key)
    statement = _restrict_to_media_in_channel(statement, media_class)

    outdated_items = session.exec(statement).all()
    logger.info(
        f"[{plugin_key}] Found {len(outdated_items)} outdated {media_type_name}",
    )

    plugin_instance = plugin_class(session)
    updated_count = 0
    for item in outdated_items:
        if stop_event.is_set():
            logger.info(
                f"[{plugin_key}] Stop requested; skipping remaining {media_type_name}",
            )
            break
        logger.info(f"[{plugin_key}] Updating {media_type_name}: {item.key}")
        try:
            getattr(plugin_instance, update_method_name)(item)

            logger.info(
                f"[{plugin_key}] Successfully updated {media_type_name}: {item.key}",
            )
            updated_count += 1

            session.commit()
        except Exception as error:
            logger.exception(
                f"[{plugin_key}] Failed to update {media_type_name}: {item.key}",
            )
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

    logger.info(
        f"[{plugin_key}] Updated {updated_count} out of {len(outdated_items)} "
        f"outdated {media_type_name}",
    )


def _update_plugin(
    plugin_key: str,
    plugin_class: type[AbstractPlugin],
    stop_event: threading.Event,
) -> None:
    """Run the full update sequence for a single plugin in its own session."""
    logger.info(f"[{plugin_key}] Starting update run")
    with Session(engine) as session:
        for media_class in MEDIA_CLASSES_IN_ORDER:
            if stop_event.is_set():
                break
            _process_outdated_items(
                session,
                media_class,
                plugin_key,
                plugin_class,
                stop_event,
            )
    logger.info(f"[{plugin_key}] Finished update run")


def _plugin_user_plugin_keys() -> list[str]:
    """Return the keys of every `Plugin` owned by the plugin user, from the database."""
    with Session(engine) as session:
        return list(
            session.exec(
                select(Plugin.key)
                .join(User, Plugin.user_id == User.id)  # type: ignore[arg-type]
                .where(User.email == PLUGIN_USER_EMAIL),
            ).all(),
        )


def _next_update_at(session: Session) -> datetime | None:
    """Return the soonest future `update_at` across the plugin user's media, if any.

    Items already due (`update_at <= now`) are excluded because they are handled by the
    run that just finished; this is only used to decide how long to wait for the next one
    to come due. Media that no channel includes is excluded so the wait is not cut short
    by an item that the update run would skip.
    """
    now = tz_datetime.now()
    soonest: datetime | None = None
    for media_class in MEDIA_CLASSES_IN_ORDER:
        statement = (
            _restrict_to_media_in_channel(
                _restrict_to_plugin_user(
                    media_class.select_with_plugin().where(
                        col(media_class.update_at) > now,
                        col(media_class.deleted_at).is_(None),
                    ),
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


def _seconds_until_next_update() -> float:
    with Session(engine) as session:
        next_update_at = _next_update_at(session)
    if next_update_at is None:
        return MAX_SLEEP_SECONDS
    seconds_until_due = (next_update_at - tz_datetime.now()).total_seconds()
    return max(0.0, min(seconds_until_due, MAX_SLEEP_SECONDS))


def _update_outdated(stop_event: threading.Event) -> None:
    # The work is grouped by the `Plugin` rows in the database (not the installed plugin
    # files). Each database plugin runs its whole update sequence in its own thread and
    # session so plugins update at the same time; the installed plugin class is only used
    # to execute the updates. Ordering is preserved within a plugin (see
    # MEDIA_CLASSES_IN_ORDER), while different plugins are independent of each other.
    plugin_classes_by_key = {plugin.plugin_key(): plugin for plugin in plugins}

    tasks: list[tuple[str, type[AbstractPlugin]]] = []
    for plugin_key in _plugin_user_plugin_keys():
        plugin_class = plugin_classes_by_key.get(plugin_key)
        if plugin_class is None:
            logger.error(
                f"[{plugin_key}] No installed plugin matches this database entry",
            )
            continue
        tasks.append((plugin_key, plugin_class))

    max_workers = min(max(len(tasks), 1), settings.UPDATE_MAX_THREADS)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_update_plugin, plugin_key, plugin_class, stop_event): (
                plugin_key
            )
            for plugin_key, plugin_class in tasks
        }
        for future in as_completed(futures):
            plugin_key = futures[future]
            try:
                future.result()
            except Exception:
                # Log the plugin-level failure and let the other plugins finish.
                logger.exception(f"[{plugin_key}] Plugin update run crashed")


def run_forever(stop_event: threading.Event) -> None:  # noqa: D103
    while not stop_event.is_set():
        _update_outdated(stop_event)
        if stop_event.is_set():
            break

        wait_seconds = _seconds_until_next_update()
        logger.info(f"Next update due in {wait_seconds:.0f}s; waiting")

        # Interruptible sleep: returns immediately if a stop is requested mid-wait.
        if stop_event.wait(timeout=wait_seconds):
            break


if __name__ == "__main__":
    configure_logging()

    run_forever(threading.Event())
    logger.info("Outdated source update process stopped")
