# TODO: Validate

from loguru import logger
from sqlmodel import Session, select
from tqdm import tqdm

from app.database import engine, load_models
from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from plugins.utils.manage_plugins import (
    import_plugins,
    plugins,
)

import_plugins()
load_models()


# TODO: Validate
def reimport_all_titles(session: Session) -> None:
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    listed = session.exec(
        select(Title.source_id, Title.key, Title.name, Plugin.key)
        .select_from(Title)
        .join(Source)
        .join(Plugin),
    ).all()

    progress = tqdm(listed, unit="title")
    for source_id, title_key, title_name, plugin_key in progress:
        progress.set_description(title_name or title_key)
        plugin_class = plugin_classes_by_key.get(plugin_key)

        if plugin_class is None:
            logger.warning(
                f"Skipping {title_name}, plugin {plugin_key} is not installed",
            )
            continue

        title = session.get_one(Title, (source_id, title_key))
        plugin_instance = plugin_class(session, title.source.plugin)
        plugin_instance.update_title(title, force=True)
        session.commit()


if __name__ == "__main__":
    logger.remove()
    logger.add(lambda message: tqdm.write(message, end=""))

    with Session(engine) as session:
        reimport_all_titles(session)

    logger.info("Reimport completed")
