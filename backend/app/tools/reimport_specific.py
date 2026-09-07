# TODO: Validate

import sys
import uuid

from loguru import logger
from sqlmodel import Session

from app.database import engine, load_models
from app.titles.models import Title
from plugins.utils.manage_plugins import (
    import_plugins,
    plugins,
)

import_plugins()
load_models()


# TODO: Validate
def reimport_single_title(session: Session, title_id: uuid.UUID) -> None:
    """Read one `Title` again from the website it came from."""
    title = session.exec(Title.select_with_plugin().where(Title.id == title_id)).one()
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    plugin_class = plugin_classes_by_key[title.source.plugin.key]

    logger.info(f"Reimporting {title.name or title.key} from {title.source.plugin.key}")
    plugin_instance = plugin_class(session, title.source.plugin)
    plugin_instance.update_title(title, force=True)
    session.commit()


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_single_title(session, uuid.UUID(sys.argv[1]))

    logger.info("Reimport completed")
