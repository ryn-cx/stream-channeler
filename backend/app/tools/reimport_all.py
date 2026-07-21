# TODO: Validate

from loguru import logger
from sqlmodel import Session, col, select

from app.database import engine, load_models
from app.shows.models import Show
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


def reimport_all_shows(session: Session) -> None:
    shows = session.exec(
        select(Show).where(
            col(Show.url).is_not(None),
            col(Show.deleted_at).is_(None),
        ),
    ).all()

    for show in shows:
        if show.url is None:
            continue
        for plugin in plugins:
            if plugin.is_valid_url_format(show.url) and plugin.implements("import_url"):
                plugin_instance = plugin(session)
                plugin_instance.import_url(show.url)
                session.commit()
                break


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_all_shows(session)

    logger.info("Reimport completed")
