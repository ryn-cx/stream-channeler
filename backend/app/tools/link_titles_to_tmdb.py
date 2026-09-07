# TODO: Validate

from collections.abc import Sequence

from loguru import logger
from sqlmodel import Session, col
from tqdm import tqdm

from app.database import engine, load_models
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.titles.models import Title
from app.titles.service.canonical import link_title_to_tmdb_lookups
from plugins.utils.manage_plugins import (
    import_plugins,
    plugins,
)

import_plugins()
load_models()


# TODO: Validate
def _titles_due_for_linking(session: Session) -> Sequence[Title]:
    return session.exec(
        Title.select_with_plugin()
        .where(col(Title.link_status).is_(None))
        .where(Plugin.key != TMDB_PLUGIN_KEY)
        .order_by(col(Title.modified_at).asc()),
    ).all()


# TODO: Validate
def _linked_status(title: Title) -> str:
    if title.canonical_title_links:
        return "Linked"
    return "Unmatched"


# TODO: Validate
def link_titles_to_tmdb(session: Session) -> None:
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    titles = _titles_due_for_linking(session)

    progress = tqdm(titles, unit="title")
    for title in progress:
        progress.set_description(title.name or title.key)
        plugin_key = title.source.plugin.key
        plugin_class = plugin_classes_by_key.get(plugin_key)

        if plugin_class is None:
            logger.warning(
                f"Skipping {title.name or title.key}, "
                f"plugin {plugin_key} is not installed",
            )
            continue

        logger.info(f"[{plugin_key}] Linking to TMDB: {title.name or title.key}")
        plugin_instance = plugin_class(session, title.source.plugin)
        try:
            link_title_to_tmdb_lookups(
                session,
                title,
                plugin_instance.tmdb_lookup_info(title.key),
            )
        except NotImplementedError:
            logger.info(f"[{plugin_key}] Does not look its titles up on TMDB")
            session.rollback()
            title.link_status = "Unsupported"
        except Exception:  # noqa: BLE001
            logger.exception(f"[{plugin_key}] Failed to link {title.key} to TMDB")
            session.rollback()
            title.link_status = "Failed"
        else:
            title.link_status = _linked_status(title)
        session.add(title)
        session.commit()


if __name__ == "__main__":
    logger.remove()
    logger.add(lambda message: tqdm.write(message, end=""))

    with Session(engine) as session:
        link_titles_to_tmdb(session)

    logger.info("Linking completed")
