# TODO: Validate

from loguru import logger
from sqlmodel import Session

from app.database import engine, load_models
from app.plugins.plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


def reimport_single_url(session: Session) -> None:
    url = "DUMMY URL"

    for plugin in plugins:
        if plugin.is_valid_url_format(url):
            plugin_instance = plugin(session)
            plugin_instance.import_url(url)


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_single_url(session)

    logger.info("Reimport completed")
