# TODO: Validate

from loguru import logger
from sqlmodel import Session

from app.database import engine, load_models
from app.plugins.models import Plugin
from app.shows.models import Show
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


# TODO: Validate
def reimport_all_shows(session: Session) -> None:
    plugin_classes_by_key = {plugin.plugin_key(): plugin for plugin in plugins}
    shows = session.exec(
        Show.select_with_plugin()
        .join(User, Plugin.user_id == User.id)  # type: ignore[arg-type]
        .where(
            User.email == PLUGIN_USER_EMAIL,
        ),
    ).all()

    for show in shows:
        plugin_class = plugin_classes_by_key[show.source.plugin.key]
        plugin_instance = plugin_class(session)
        plugin_instance.update_show(show, force=True)
        session.commit()


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_all_shows(session)

    logger.info("Reimport completed")
