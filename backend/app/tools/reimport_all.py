# TODO: Validate

from loguru import logger
from sqlmodel import Session

from app.database import engine, load_models
from app.titles.models import Title
from app.titles.service.canonical import match_title_to_tmdb
from plugins.utils.manage_plugins import (
    import_plugins,
    plugins,
)

import_plugins()
load_models()


# TODO: Validate
def reimport_all_titles(session: Session) -> None:
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    titles = session.exec(
        Title.select_with_plugin(),
    ).all()

    for title in titles:
        plugin_class = plugin_classes_by_key[title.source.plugin.key]
        plugin_instance = plugin_class(session, title.source.plugin)
        plugin_instance.update_title(title, force=True)
        match_title_to_tmdb(session, title)
        session.commit()


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_all_titles(session)

    logger.info("Reimport completed")
