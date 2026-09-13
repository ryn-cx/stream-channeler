# TODO: Validate

from loguru import logger
from sqlmodel import Session, col
from tqdm import tqdm

from app.database import engine, load_models
from app.titles.models import Title
from app.titles.service.linking import _old_relink_episode
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
def relink_episodes(session: Session, selection: PluginSelection | None = None) -> None:
    selection = selection or PluginSelection()
    linked_titles = session.exec(
        Title.select_with_plugin()
        .where(is_linked(Title), col(Title.deleted_at).is_(None))
        .where(*selection_clauses(selection))
        .order_by(col(Title.modified_at).asc()),
    ).all()

    progress = tqdm(linked_titles, unit="title")
    for title in progress:
        progress.set_description(title.__str__())
        _old_relink_episode(session, title)
        session.commit()


if __name__ == "__main__":
    selected = parse_selection("Match every non-canonical title to TMDB again.")

    logger.remove()
    logger.add(lambda message: tqdm.write(message, end=""))
    logger.info(f"Relinking {selection_description(selected)}")

    with Session(engine) as session:
        relink_episodes(session, selected)

    logger.info("Relinking completed")
