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

    logger.info(f"Reimporting {len(titles)} titles")

    for index, title in enumerate(titles, start=1):
        logger.info(f"[{index}/{len(titles)}] Reimporting {title.name} ({title.id})")
        plugin_class = plugin_classes_by_key.get(title.source.plugin.key)

        if plugin_class is None:
            logger.warning(
                f"[{index}/{len(titles)}] Skipping {title.name}, "
                f"plugin {title.source.plugin.key} is not installed",
            )
            continue

        plugin_instance = plugin_class(session, title.source.plugin)
        plugin_instance.update_title(title, force=True)
        logger.info(f"[{index}/{len(titles)}] Matching {title.name} to TMDB")
        match_title_to_tmdb(session, title)
        session.commit()
        logger.info(f"[{index}/{len(titles)}] Finished {title.name}")


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_all_titles(session)

    logger.info("Reimport completed")
