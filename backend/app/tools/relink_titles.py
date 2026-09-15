# TODO: Validate

from loguru import logger
from sqlmodel import Session, col
from tqdm import tqdm

from app.database import engine, load_models
from app.titles.models import Title
from app.titles.service.linking import relink_title
from app.tmdb_media.filters import is_linked
from app.tools.selection import (
    PluginSelection,
    parse_selection,
    selection_clauses,
    selection_description,
)
from plugins.utils.manage_plugins import import_plugins

import_plugins()
load_models()


# TODO: Validate
def relink_titles(session: Session, selection: PluginSelection | None = None) -> None:
    selection = selection or PluginSelection()
    linked_titles = session.exec(
        Title.select_with_plugin()
        .where(is_linked(Title), col(Title.deleted_at).is_(None))
        .where(*selection_clauses(selection))
        .order_by(col(Title.modified_at).asc()),
    ).all()

    progress = tqdm(linked_titles, unit="title")
    for title in progress:
        plugin_key = title.source.plugin.key
        progress.set_description(f"[{plugin_key}] {title.name or title.key}")
        try:
            relink_title(session, title)
        except Exception:  # noqa: BLE001
            logger.exception(f"Failed to relink {title.key} to TMDB")
            session.rollback()
            continue
        session.commit()


if __name__ == "__main__":
    selected = parse_selection(
        "Match every non-canonical title against TMDB again.",
    )

    logger.remove()
    logger.add(lambda message: tqdm.write(message, end=""))
    logger.info(f"Relinking {selection_description(selected)}")

    with Session(engine) as session:
        relink_titles(session, selected)

    logger.info("Relinking completed")
