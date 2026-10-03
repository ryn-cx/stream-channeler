# TODO: Validate

import queue
import uuid
from argparse import ArgumentParser
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

from loguru import logger
from sqlmodel import Session, col, select
from tqdm import tqdm

from app.database import engine, load_models
from app.log import configure_logging, progress_bar
from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from app.titles.service.linking import link_title
from app.tools.selection import (
    PluginSelection,
    add_selection_arguments,
    add_threads_argument,
    selection_clauses,
    selection_description,
    selection_from_arguments,
    user_channel_clauses,
)
from plugins.utils.base_plugin.files import bypass_file_updates
from plugins.utils.manage_plugins import (
    import_plugins,
    plugins,
)

import_plugins()
load_models()


# TODO: Validate
def _reimport_title(
    session: Session,
    plugin_records: dict[str, Plugin],
    source_id: uuid.UUID,
    title_key: str,
    plugin_key: str,
) -> None:
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    if plugin_key not in plugin_records:
        plugin_records[plugin_key] = Plugin.get_one(session, plugin_key)
    title = session.get(Title, (source_id, title_key))
    if title is None:
        return
    plugin_instance = plugin_classes_by_key[plugin_key](
        session,
        plugin_records[plugin_key],
    )
    plugin_instance.update_title(title)
    session.commit()
    link_title(session, title)
    session.commit()


# TODO: Validate
def _reimport_worker(
    listed: queue.SimpleQueue[tuple[uuid.UUID, str, str | None, str]],
    progress: tqdm[Any],
    progress_lock: Lock,
    failures: list[str],
) -> None:
    with Session(engine, expire_on_commit=False) as session, bypass_file_updates():
        plugin_records: dict[str, Plugin] = {}
        while True:
            try:
                source_id, title_key, title_name, plugin_key = listed.get_nowait()
            except queue.Empty:
                return

            label = f"[{plugin_key}] {title_name or title_key}"
            with progress_lock:
                progress.set_description(label)

            try:
                _reimport_title(
                    session,
                    plugin_records,
                    source_id,
                    title_key,
                    plugin_key,
                )
            except Exception:  # noqa: BLE001
                session.rollback()
                plugin_records.clear()
                logger.exception(f"Failed to reimport {label}")
                with progress_lock:
                    failures.append(label)

            with progress_lock:
                progress.update()


# TODO: Validate
def reimport_all_titles(
    selection: PluginSelection | None = None,
    threads: int = 1,
) -> None:
    selection = selection or PluginSelection()
    with Session(engine, expire_on_commit=False) as session:
        listed = session.exec(
            select(Title.source_id, Title.key, Title.name, Plugin.key)
            .select_from(Title)
            .join(Source)
            .join(Plugin)
            .where(*selection_clauses(selection))
            .where(*user_channel_clauses(selection))
            .order_by(col(Title.upserted_at)),
        ).all()

    reimport_titles(listed, threads)


# TODO: Validate
def reimport_titles(
    listed: Sequence[tuple[uuid.UUID, str, str | None, str]],
    threads: int = 1,
) -> None:
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
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
    failures: list[str] = []
    with (
        progress_bar(total=total, unit="title") as progress,
        ThreadPoolExecutor(max_workers=threads) as executor,
    ):
        futures = [
            executor.submit(
                _reimport_worker,
                pending,
                progress,
                progress_lock,
                failures,
            )
            for _ in range(threads)
        ]
        for future in as_completed(futures):
            future.result()

    if failures:
        logger.warning(
            f"{len(failures)} of {total} titles failed to reimport:\n"
            + "\n".join(failures),
        )


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Read every title again from the website it came from.",
    )
    add_selection_arguments(parser)
    add_threads_argument(parser)
    arguments = parser.parse_args()
    selected = selection_from_arguments(arguments)

    configure_logging()
    logger.info(
        f"Reimporting {selection_description(selected)} "
        f"on {arguments.threads} thread{'s' if arguments.threads > 1 else ''}",
    )

    reimport_all_titles(selected, threads=arguments.threads)

    logger.info("Reimport completed")
