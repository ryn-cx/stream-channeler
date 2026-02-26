# TODO: Validate
import traceback

from loguru import logger
from sqlalchemy import event
from sqlmodel import Session, col, select

from app.database import engine, load_models
from app.media.models import Show
from app.plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


def count_statements(*_args: object, **_kwargs: object) -> None:
    stack: list[traceback.FrameSummary] = traceback.extract_stack()
    callers: list[str] = [
        f"{frame.filename}:{frame.lineno} in {frame.name}"
        for frame in stack
        if ".venv" not in frame.filename
    ]
    callers_str: str = "\n  ".join(callers)

    logger.trace(f"Stack trace:\n {callers_str}")


if __name__ == "__main__":
    with Session(engine) as session:
        event.listen(Session, "do_orm_execute", count_statements)

        statement = select(Show).order_by(col(Show.modified_at))
        shows = session.exec(statement).all()

        for show in shows:
            logger.info(f"Updating show: {show.name} (source: {show.source.name})")
            for plugin in plugins:
                if plugin.plugin_id() == show.source.plugin.key:
                    plugin_instance = plugin(session)
                    plugin_instance.update_show(show)
                    session.commit()
                    break
            else:
                logger.error(
                    f"No matching plugin found for show: {show.name} (plugin_id: {show.source.plugin.key})",
                )
