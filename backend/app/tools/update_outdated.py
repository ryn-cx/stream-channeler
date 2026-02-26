# TODO: Validate

import sys

from loguru import logger
from pyinstrument import Profiler
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.database import engine, load_models
from app.media.models import Episode, Season, Show, Source
from app.plugins.utils.ip_validator import IPValidationError
from app.plugins.utils.manage_plugins import import_plugins, plugins
from app.utils import tz_datetime

logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True)

import_plugins()
load_models()


def get_plugin_id(item: Source | Show | Season | Episode) -> str:
    """Get the plugin_id for a given media item.

    Args:
        item: Media item (Source, Show, Season, or Episode)

    Returns:
        The plugin key/id associated with this item

    Raises:
        TypeError: If the item type is not supported
    """
    if isinstance(item, Source):
        return item.plugin.key
    if isinstance(item, Show):
        return item.source.plugin.key
    if isinstance(item, Season):
        return item.show.source.plugin.key

    return item.season.show.source.plugin.key

    msg = f"Unsupported media type: {type(item)}"
    raise TypeError(msg)


# TODO: This code is not production ready.
def update_outdated_media(
    session: Session,
    media_class: type[Source | Show | Season | Episode],
    media_type_name: str,
) -> None:
    """Update outdated entries for a specific media type.

    Args:
        session: Database session
        media_class: SQLModel class (Source, Show, Season, or Episode)
        media_type_name: Human-readable name for logging
    """
    statement = (
        select(media_class)
        .where(
            col(media_class.update_at) > col(media_class.data_timestamp),
            col(media_class.update_at) < tz_datetime.now(),
        )
        .order_by(col(media_class.update_at).asc())
    )

    if media_class == Source:
        statement = statement.options(selectinload(Source.plugin))
    elif media_class == Show:
        statement = statement.options(
            selectinload(Show.source).selectinload(Source.plugin),
        )
    elif media_class == Season:
        statement = statement.options(
            selectinload(Season.show)
            .selectinload(Show.source)
            .selectinload(Source.plugin),
        )
    elif media_class == Episode:
        statement = statement.options(
            selectinload(Episode.season)
            .selectinload(Season.show)
            .selectinload(Show.source)
            .selectinload(Source.plugin),
        )

    outdated_items = session.exec(statement).all()
    logger.info(f"Found {len(outdated_items)} outdated {media_type_name}")

    updated_count = 0

    for item in outdated_items:
        profiler = Profiler()

        plugin_id = get_plugin_id(item)
        item_name = getattr(item, "name", None) or item.key
        logger.info(
            f"Updating {media_type_name}: {item_name} (plugin: {plugin_id})",
        )

        profiler.start()

        for plugin in plugins:
            if plugin.plugin_id() == plugin_id:
                plugin_instance = plugin(session)

                try:
                    # Call appropriate update method
                    if isinstance(item, Source):
                        plugin_instance.update_source(item)
                    elif isinstance(item, Show):
                        plugin_instance.update_show(item)
                    elif isinstance(item, Season):
                        plugin_instance.update_season(item)
                    elif isinstance(item, Episode):  # type: ignore[reportUnnecessaryIsInstance] - Makes code prettier
                        plugin_instance.update_episode(item)

                    logger.info(
                        f"Successfully updated {media_type_name}: {item_name}",
                    )
                    updated_count += 1

                    session.commit()
                    session.refresh(item)
                except IPValidationError:
                    logger.warning(
                        f"Skipping update for {media_type_name}: {item_name} - IP validation failed",
                    )
                break
        else:
            session.rollback()
            logger.error(
                f"No matching plugin found for {media_type_name}: {item_name} (plugin_id: {plugin_id})",
            )

        profiler.stop()

        logger.info(
            f"Profile for {media_type_name} {item_name}:\n{profiler.output_text(unicode=True, color=True)}",
        )

    logger.info(
        f"Updated {updated_count} out of {len(outdated_items)} outdated {media_type_name}",
    )


if __name__ == "__main__":
    with Session(engine) as session:
        update_outdated_media(session, Source, "source")
        update_outdated_media(session, Show, "show")
        update_outdated_media(session, Season, "season")
        update_outdated_media(session, Episode, "episode")

    logger.info("Outdated source update process completed")
