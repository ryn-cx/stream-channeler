# TODO: Validate

import sys
import uuid
from collections.abc import Callable
from typing import Any

from loguru import logger
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.database import engine, load_models
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.plugins.plugins.utils.ip_validator import IPValidationError
from app.plugins.plugins.utils.manage_plugins import import_plugins, plugins
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime

logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True)

import_plugins()
load_models()


def _process_outdated_items(
    media_class: type[Source | Show | Season | Episode],
    media_type_name: str,
    join_and_load: Callable[[Any], Any],
    get_plugin_key: Callable[[Any], str],
    update_method_name: str,
) -> None:
    # Phase 1: Query outdated items and collect identifiers
    item_infos: list[tuple[uuid.UUID, str, str]] = []
    with Session(engine) as session:
        statement = (
            select(media_class)
            .where(
                col(media_class.update_at) > col(media_class.data_timestamp),
                col(media_class.update_at) < tz_datetime.now(),
            )
            .order_by(col(media_class.update_at).asc())
        )
        outdated_items = session.exec(join_and_load(statement)).all()
        item_infos = [
            (item.id, get_plugin_key(item), getattr(item, "name", None) or item.key)
            for item in outdated_items
        ]

    logger.info(f"Found {len(item_infos)} outdated {media_type_name}")

    # Phase 2: Process each item in an isolated session
    updated_count = 0

    for item_id, plugin_id, item_name in item_infos:
        logger.info(
            f"Updating {media_type_name}: {item_name} (plugin: {plugin_id})",
        )

        with Session(engine) as item_session:
            item = item_session.exec(
                select(media_class).where(media_class.id == item_id),
            ).first()

            if not item:
                logger.warning(
                    f"Item no longer exists: {item_name} ({item_id})",
                )
                continue

            for plugin in plugins:
                if plugin.plugin_id() == plugin_id:
                    plugin_instance = plugin(item_session)

                    try:
                        getattr(plugin_instance, update_method_name)(item)

                        logger.info(
                            f"Successfully updated {media_type_name}: {item_name}",
                        )
                        updated_count += 1

                        item_session.commit()
                    except IPValidationError:
                        logger.warning(
                            f"Skipping update for {media_type_name}: {item_name} - IP validation failed",
                        )
                    break
            else:
                logger.error(
                    f"No matching plugin found for {media_type_name}: {item_name} (plugin_id: {plugin_id})",
                )

    logger.info(
        f"Updated {updated_count} out of {len(item_infos)} outdated {media_type_name}",
    )


def update_outdated_sources() -> None:
    def join_and_load(statement: Any) -> Any:
        return (
            statement.join(Plugin)
            .where(
                col(Plugin.user_id).is_(None),
            )
            .options(selectinload(Source.plugin))
        )

    _process_outdated_items(
        Source,
        "source",
        join_and_load,
        lambda s: s.plugin.key,
        "update_source",
    )


def update_outdated_shows() -> None:
    def join_and_load(statement: Any) -> Any:
        return (
            statement.join(Source)
            .join(Plugin)
            .where(
                col(Plugin.user_id).is_(None),
            )
            .options(selectinload(Show.source).selectinload(Source.plugin))
        )

    _process_outdated_items(
        Show,
        "show",
        join_and_load,
        lambda s: s.source.plugin.key,
        "update_show",
    )


def update_outdated_seasons() -> None:
    def join_and_load(statement: Any) -> Any:
        return (
            statement.join(Show)
            .join(Source)
            .join(Plugin)
            .where(
                col(Plugin.user_id).is_(None),
            )
            .options(
                selectinload(Season.show)
                .selectinload(Show.source)
                .selectinload(Source.plugin),
            )
        )

    _process_outdated_items(
        Season,
        "season",
        join_and_load,
        lambda s: s.show.source.plugin.key,
        "update_season",
    )


def update_outdated_episodes() -> None:
    def join_and_load(statement: Any) -> Any:
        return (
            statement.join(Season)
            .join(Show)
            .join(Source)
            .join(Plugin)
            .where(
                col(Plugin.user_id).is_(None),
            )
            .options(
                selectinload(Episode.season)
                .selectinload(Season.show)
                .selectinload(Show.source)
                .selectinload(Source.plugin),
            )
        )

    _process_outdated_items(
        Episode,
        "episode",
        join_and_load,
        lambda e: e.season.show.source.plugin.key,
        "update_episode",
    )


if __name__ == "__main__":
    update_outdated_sources()
    update_outdated_shows()
    update_outdated_seasons()
    update_outdated_episodes()

    logger.info("Outdated source update process completed")
