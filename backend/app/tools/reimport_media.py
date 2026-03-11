# # TODO: Validate
# import traceback

# from loguru import logger
# from sqlalchemy import event
# from sqlmodel import Session

# from app.database import engine, load_models
# from app.plugins.plugins.utils.manage_plugins import import_plugins, plugins

# import_plugins()
# load_models()


# def count_statements(*_args: object, **_kwargs: object) -> None:
#     stack: list[traceback.FrameSummary] = traceback.extract_stack()
#     callers: list[str] = [
#         f"{frame.filename}:{frame.lineno} in {frame.name}"
#         for frame in stack
#         if ".venv" not in frame.filename
#     ]
#     callers_str: str = "\n  ".join(callers)

#     logger.trace(f"Stack trace:\n {callers_str}")


# if __name__ == "__main__":
#     with Session(engine) as session:
#         event.listen(Session, "do_orm_execute", count_statements)

#         for plugin in plugins:
#             logger.info(f"Rebuilding plugin: {plugin.plugin_id()}")
#             plugin.rebuild_shows(session)
#             session.commit()
