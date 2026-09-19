# TODO: Validate

import queue
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from loguru import logger
from sqlmodel import Session, col, select
from tqdm import tqdm

from app.database import engine, load_models
from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from app.tools.selection import (
    PluginSelection,
    parse_selection,
    selection_clauses,
    selection_description,
)
from plugins.utils.base_plugin.files import bypass_file_updates
from plugins.utils.manage_plugins import (
    import_plugins,
    plugins,
)

import_plugins()
load_models()


# TODO: Validate
def _reimport_worker(
    listed: queue.SimpleQueue[tuple[uuid.UUID, str, str | None, str]],
    progress: tqdm[Any],
    progress_lock: Lock,
) -> None:
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    with Session(engine) as session, bypass_file_updates():
        plugin_records: dict[str, Plugin] = {}
        while True:
            try:
                source_id, title_key, title_name, plugin_key = listed.get_nowait()
            except queue.Empty:
                return

            with progress_lock:
                progress.set_description(f"[{plugin_key}] {title_name or title_key}")

            if plugin_key not in plugin_records:
                plugin_records[plugin_key] = Plugin.get_one(session, plugin_key)
            title = session.get_one(Title, (source_id, title_key))
            plugin_instance = plugin_classes_by_key[plugin_key](
                session,
                plugin_records[plugin_key],
            )
            plugin_instance.update_title(title)
            session.commit()

            with progress_lock:
                progress.update()


# TODO: Validate
def reimport_all_titles(selection: PluginSelection | None = None) -> None:
    selection = selection or PluginSelection()
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    with Session(engine) as session:
        listed = session.exec(
            select(Title.source_id, Title.key, Title.name, Plugin.key)
            .select_from(Title)
            .join(Source)
            .join(Plugin)
            .where(*selection_clauses(selection))
            .order_by(col(Title.modified_at)),
        ).all()

    pending: queue.SimpleQueue[tuple[uuid.UUID, str, str | None, str]] = (
        queue.SimpleQueue()
    )
    total = 0
    for source_id, title_key, title_name, plugin_key in listed:
        if plugin_key not in plugin_classes_by_key:
            logger.warning(
                f"Skipping {title_name}, plugin {plugin_key} is not installed",
            )
            continue
        pending.put((source_id, title_key, title_name, plugin_key))
        total += 1

    if not total:
        return

    progress_lock = Lock()
    workers = 1
    with (
        tqdm(total=total, unit="title") as progress,
        ThreadPoolExecutor(max_workers=workers) as executor,
    ):
        futures = [
            executor.submit(_reimport_worker, pending, progress, progress_lock)
            for _ in range(workers)
        ]
        for future in as_completed(futures):
            future.result()


if __name__ == "__main__":
    selected = parse_selection("Read every title again from the website it came from.")

    logger.remove()
    logger.add(lambda message: tqdm.write(message, end=""))
    logger.info(f"Reimporting {selection_description(selected)}")

    reimport_all_titles(selected)

    logger.info("Reimport completed")
