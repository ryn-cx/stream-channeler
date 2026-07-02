# TODO: Validate
# pyright: reportArgumentType=false

import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, select

from app.channels.models import ChannelSeasonFilter, ChannelShow
from app.database import automatically_import_models, engine
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import import_plugins, plugins

logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True)

import_plugins()
automatically_import_models()

MediaModel = Plugin | Source | Show | Season | Episode


def _get_plugin_key_plugin(plugin: Plugin) -> str:
    return plugin.key


def _get_plugin_key_source(s: Source) -> str:
    return s.plugin.key


def _get_plugin_key_show(s: Show) -> str:
    return s.source.plugin.key


def _get_plugin_key_season(s: Season) -> str:
    return s.show.source.plugin.key


def _get_plugin_key_episode(e: Episode) -> str:
    return e.season.show.source.plugin.key


MODEL_VALUES: dict[
    type[MediaModel],
    tuple[list[type], LoaderOption | None, Callable[..., str]],
] = {
    # Plugin is its own root record, so no join chain or eager loading is needed
    # to resolve its plugin key.
    Plugin: (
        [],
        None,
        _get_plugin_key_plugin,
    ),
    Source: (
        [Plugin],
        selectinload(Source.plugin),  # type: ignore[arg-type]
        _get_plugin_key_source,
    ),
    Show: (
        [Source, Plugin],
        selectinload(Show.source).selectinload(Source.plugin),  # type: ignore[arg-type]
        _get_plugin_key_show,
    ),
    Season: (
        [Show, Source, Plugin],
        (
            selectinload(Season.show)  # type: ignore[arg-type]
            .selectinload(Show.source)  # type: ignore[arg-type]
            .selectinload(Source.plugin)  # type: ignore[arg-type]
        ),
        _get_plugin_key_season,
    ),
    Episode: (
        [Season, Show, Source, Plugin],
        (
            selectinload(Episode.season)  # type: ignore[arg-type]
            .selectinload(Season.show)  # type: ignore[arg-type]
            .selectinload(Show.source)  # type: ignore[arg-type]
            .selectinload(Source.plugin)  # type: ignore[arg-type]
        ),
        _get_plugin_key_episode,
    ),
}


def _channel_inclusion_clause() -> ColumnElement[bool]:
    return or_(
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


# Media classes are updated in this order per plugin because updating a plugin (e.g.
# JustWatch) can mark its own sources outdated, which the Source pass then picks up in
# the same run; the same cascade applies down the Source -> Show -> Season -> Episode
# chain.
MEDIA_CLASSES_IN_ORDER: tuple[type[MediaModel], ...] = (
    Plugin,
    Source,
    Show,
    Season,
    Episode,
)


def _process_outdated_items(
    session: Session,
    media_class: type[MediaModel],
    plugin_key: str,
    plugin_class: type[AbstractPlugin],
) -> None:
    join_chain, load_options, _get_plugin_key = MODEL_VALUES[media_class]
    media_type_name = media_class.__name__.lower()
    update_method_name = f"update_{media_type_name}"

    statement = (
        select(media_class)
        .where(
            col(media_class.update_at).is_not(None),
            col(media_class.update_at) < tz_datetime.now(),
            col(media_class.deleted_at).is_(None),
        )
        .order_by(col(media_class.update_at).asc())
    )
    for model in join_chain:
        statement = statement.join(model)
    # Skip items whose Season is not included in any channel. Source is
    # exempt because updating a Source is how new Shows are discovered.
    if media_class is Show:
        statement = statement.where(_show_has_season_in_channel_exists())
    elif media_class in (Season, Episode):
        statement = statement.where(_season_in_channel_exists())
    statement = (
        statement.join(User, Plugin.user_id == User.id)  # type: ignore[arg-type]
        .where(User.email == PLUGIN_USER_EMAIL)
        # Only this plugin's media so each plugin's run is independent.
        .where(col(Plugin.key) == plugin_key)
    )
    if load_options is not None:
        statement = statement.options(load_options)

    outdated_items = session.exec(statement).all()
    logger.info(
        f"[{plugin_key}] Found {len(outdated_items)} outdated {media_type_name}",
    )

    plugin_instance = plugin_class(session)
    updated_count = 0
    for item in outdated_items:
        logger.info(f"[{plugin_key}] Updating {media_type_name}: {item.key}")
        try:
            getattr(plugin_instance, update_method_name)(item)

            logger.info(
                f"[{plugin_key}] Successfully updated {media_type_name}: {item.key}",
            )
            updated_count += 1

            session.commit()
        except Exception:  # noqa: BLE001 - This should catch ALL exceptions.
            logger.exception(
                f"[{plugin_key}] Failed to update {media_type_name}: {item.key}",
            )
            # If any error occurs, roll back changes then set update_at at
            # the maximum possible value to avoid retrying the update until
            # the issue is resolved.
            session.rollback()
            session.refresh(item)
            item.update_at = tz_datetime.max()
            session.commit()

    logger.info(
        f"[{plugin_key}] Updated {updated_count} out of {len(outdated_items)} "
        f"outdated {media_type_name}",
    )


def _update_plugin(plugin_key: str, plugin_class: type[AbstractPlugin]) -> None:
    """Run the full update sequence for a single plugin in its own session."""
    logger.info(f"[{plugin_key}] Starting update run")
    with Session(engine) as session:
        for media_class in MEDIA_CLASSES_IN_ORDER:
            _process_outdated_items(session, media_class, plugin_key, plugin_class)
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


if __name__ == "__main__":
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

    with ThreadPoolExecutor(max_workers=max(len(tasks), 1)) as executor:
        futures = {
            executor.submit(_update_plugin, plugin_key, plugin_class): plugin_key
            for plugin_key, plugin_class in tasks
        }
        for future in as_completed(futures):
            plugin_key = futures[future]
            try:
                future.result()
            except Exception:  # noqa: BLE001 - Surface a per-plugin crash.
                # Log the plugin-level failure and let the other plugins finish.
                logger.exception(f"[{plugin_key}] Plugin update run crashed")

    logger.info("Outdated source update process completed")
