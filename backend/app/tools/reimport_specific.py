# TODO: Validate

import sys
import uuid

from loguru import logger
from sqlmodel import Session

from app.database import engine, load_models
from app.shows.models import Show
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


# TODO: Validate
def reimport_single_show(session: Session, show_id: uuid.UUID) -> None:
    """Read one `Show` again from the website it came from."""
    show = session.exec(Show.select_with_plugin().where(Show.id == show_id)).one()
    plugin_classes_by_key = {plugin.plugin_key(): plugin for plugin in plugins}
    plugin_class = plugin_classes_by_key[show.source.plugin.key]

    logger.info(f"Reimporting {show.name or show.key} from {show.source.plugin.key}")
    plugin_instance = plugin_class(session)
    plugin_instance.update_show(show, force=True)
    session.commit()


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_single_show(session, uuid.UUID(sys.argv[1]))

    logger.info("Reimport completed")
