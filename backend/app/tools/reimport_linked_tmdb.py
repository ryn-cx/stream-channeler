# TODO: Validate

from argparse import ArgumentParser

from loguru import logger
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from app.database import engine
from app.log import configure_logging
from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle
from app.tools.reimport_all import reimport_titles
from app.tools.selection import (
    PluginSelection,
    add_selection_arguments,
    add_threads_argument,
    selection_clauses,
    selection_description,
    selection_from_arguments,
    user_channel_clauses,
)


# TODO: Validate
def reimport_linked_tmdb_titles(selection: PluginSelection, threads: int = 1) -> None:
    tmdb_title = aliased(Title)
    tmdb_source = aliased(Source)
    tmdb_plugin = aliased(Plugin)
    linked_tmdb_title_ids = (
        select(TitleTmdbTitle.tmdb_title_id)
        .join(Title, col(TitleTmdbTitle.title_id) == col(Title.id))
        .join(Source, col(Title.source_id) == col(Source.id))
        .join(Plugin, col(Source.plugin_id) == col(Plugin.id))
        .where(*selection_clauses(selection))
        .where(*user_channel_clauses(selection))
    )
    with Session(engine, expire_on_commit=False) as session:
        listed = session.exec(
            select(
                tmdb_title.source_id,
                tmdb_title.key,
                tmdb_title.name,
                tmdb_plugin.key,
            )
            .select_from(tmdb_title)
            .join(tmdb_source, col(tmdb_title.source_id) == col(tmdb_source.id))
            .join(tmdb_plugin, col(tmdb_source.plugin_id) == col(tmdb_plugin.id))
            .where(col(tmdb_title.id).in_(linked_tmdb_title_ids))
            .order_by(col(tmdb_title.upserted_at)),
        ).all()

    logger.info(f"Found {len(listed)} linked TMDB titles")
    reimport_titles(listed, threads)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Read every TMDB title linked to a plugin or source again from TMDB.",
    )
    add_selection_arguments(parser)
    add_threads_argument(parser)
    arguments = parser.parse_args()
    if not arguments.plugin and not arguments.source:
        parser.error("name at least one --plugin or --source")
    selected = selection_from_arguments(arguments)

    configure_logging()
    logger.info(
        f"Reimporting TMDB titles linked to {selection_description(selected)} "
        f"on {arguments.threads} thread{'s' if arguments.threads > 1 else ''}",
    )

    reimport_linked_tmdb_titles(selected, threads=arguments.threads)

    logger.info("Reimport completed")
