# TODO: Validate
"""Import every stored test file into the local developer database."""

from loguru import logger
from sqlmodel import Session

from app.constants import ALL_TEST_FILES_FOLDER
from app.database import engine, load_models
from app.files.models import File
from app.plugins.models import Plugin
from plugins.utils.manage_plugins import import_plugins, plugins
from tests.plugins.plugin_validator.stored_files import (
    stored_file_record,
    stored_key,
)

import_plugins()
load_models()

COMMIT_EVERY = 500


# TODO: Validate
def _plugin_records_by_owner_key(session: Session) -> dict[str, Plugin]:
    records: dict[str, Plugin] = {}
    for plugin_class in plugins:
        owner_key = plugin_class.__module__.split(".")[1]
        plugin = Plugin(
            key=plugin_class.plugin_name(),
        ).upsert(
            session,
            Plugin.get(session, plugin_class.plugin_name()),
        )
        plugin.set_update_at(None)
        records[owner_key] = plugin
    return records


# TODO: Validate
def sync_test_files(session: Session) -> None:
    plugin_records = _plugin_records_by_owner_key(session)
    paths = sorted(path for path in ALL_TEST_FILES_FOLDER.rglob("*") if path.is_file())
    logger.info(
        f"Importing {len(paths)} stored test files from {ALL_TEST_FILES_FOLDER}",
    )

    imported = 0
    for path in paths:
        owner_key, file_key = stored_key(path)
        plugin = plugin_records.get(owner_key)
        if plugin is None:
            logger.warning(f"No plugin named {owner_key}, skipping {file_key}")
            continue

        record = stored_file_record(owner_key, file_key, path)
        record.plugin_id = plugin.id
        record.upsert(plugin, File.get(session, plugin, file_key)).set_update_at(None)
        imported += 1
        if imported % COMMIT_EVERY == 0:
            session.commit()
            logger.info(f"Imported {imported} of {len(paths)} files")

    session.commit()
    logger.info(f"Imported {imported} files")


if __name__ == "__main__":
    with Session(engine) as session:
        sync_test_files(session)
