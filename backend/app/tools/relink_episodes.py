# TODO: Validate

from argparse import ArgumentParser
from uuid import UUID

from loguru import logger
from sqlmodel import Session, col

from app.database import engine, load_models
from app.log import configure_logging, progress_bar
from app.titles.models import Title
from app.titles.service.linking.episode_relinking import _relink_episode
from app.tmdb_media.filters import is_linked
from app.tools.selection import (
    PluginSelection,
    add_selection_arguments,
    add_threads_argument,
    selection_clauses,
    selection_description,
    selection_from_arguments,
    user_channel_clauses,
)
from app.tools.utils.threaded import run_threaded
from plugins.utils.manage_plugins import import_plugins

import_plugins()
load_models()


# TODO: Validate
def _relink_one(session: Session, title_id: UUID) -> bool:
    title = session.exec(
        Title.select_with_plugin().where(col(Title.id) == title_id),
    ).first()
    if title is None:
        return True
    _relink_episode(session, title)
    session.commit()
    return True


# TODO: Validate
def relink_episodes(
    session: Session,
    selection: PluginSelection | None = None,
    *,
    threads: int = 1,
) -> None:
    selection = selection or PluginSelection()
    linked_titles = session.exec(
        Title.select_with_plugin()
        .where(is_linked(Title), col(Title.deleted_at).is_(None))
        .where(*selection_clauses(selection))
        .where(*user_channel_clauses(selection))
        .order_by(col(Title.modified_at).asc()),
    ).all()

    if threads > 1:
        run_threaded(
            [title.id for title in linked_titles],
            _relink_one,
            threads=threads,
            unit="title",
        )
        return

    progress = progress_bar(linked_titles, unit="title")
    for title in progress:
        plugin_key = title.source.plugin.key
        progress.set_description(f"[{plugin_key}] {title.name or title.key}")
        _relink_episode(session, title)
        session.commit()


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Match every non-canonical title to TMDB again.",
    )
    add_selection_arguments(parser)
    add_threads_argument(parser)
    arguments = parser.parse_args()
    selected = selection_from_arguments(arguments)

    configure_logging()
    logger.info(f"Relinking {selection_description(selected)}")

    with Session(engine, expire_on_commit=False) as session:
        relink_episodes(
            session,
            selected,
            threads=arguments.threads,
        )

    logger.info("Relinking completed")
