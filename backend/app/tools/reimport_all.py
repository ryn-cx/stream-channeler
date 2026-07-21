# TODO: Validate

from loguru import logger
from sqlmodel import Session, col

from app.database import engine, load_models
from app.plugins.models import Plugin
from app.shows.models import Show
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


def reimport_all_shows(session: Session) -> None:
    shows = session.exec(
        Show.select_with_plugin()
        .join(User, Plugin.user_id == User.id)  # type: ignore[arg-type]
        .where(
            User.email == PLUGIN_USER_EMAIL,
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


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_all_shows(session)

    logger.info("Reimport completed")
