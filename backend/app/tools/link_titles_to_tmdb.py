# TODO: Validate


import threading

from loguru import logger
from sqlmodel import Session, col

from app.channels.channel_scope import in_a_user_channel
from app.database import engine, load_models
from app.log import configure_logging, progress_bar
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from app.titles.service.linking import link_new_title_to_tmdb
from app.tools.selection import (
    PluginSelection,
    parse_selection,
    selection_clauses,
    selection_description,
    user_channel_clauses,
)
from plugins.utils.manage_plugins import import_plugins

import_plugins()
load_models()


# TODO: Validate
def link_titles_to_tmdb(
    session: Session,
    selection: PluginSelection | None = None,
) -> None:
    selection = selection or PluginSelection()
    unlinked_titles = session.exec(
        Title.select_with_plugin()
        .where(col(Title.link_status).is_(None))
        .where(col(Source.link_to_tmdb).is_(True))
        .where(Plugin.key != TMDB_PLUGIN_KEY)
        .where(*selection_clauses(selection))
        .where(*user_channel_clauses(selection))
        .order_by(in_a_user_channel().desc(), col(Title.modified_at).asc()),
    ).all()

    if not unlinked_titles:
        return

    progress = progress_bar(unlinked_titles, unit="title")
    for title in progress:
        progress.set_description(f"{title.source.key}: {title.name or title.key}")
        try:
            link_new_title_to_tmdb(session, title)
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()
            logger.exception(f"Failed to link {title.key} to TMDB")
            title.link_status = "Failed"
            session.add(title)
            session.commit()


# TODO: Validate
def run_forever(
    stop_event: threading.Event | None = None,
    selection: PluginSelection | None = None,
) -> None:
    stop_event = stop_event or threading.Event()
    while not stop_event.is_set():
        with Session(engine, expire_on_commit=False) as session:
            link_titles_to_tmdb(session, selection)
        if stop_event.wait(timeout=60):
            break


if __name__ == "__main__":
    selected = parse_selection("Match every title that has never been matched to TMDB.")

    configure_logging()
    logger.info(f"Linking {selection_description(selected)}")

    run_forever(selection=selected)

    logger.info("Linking process stopped")
