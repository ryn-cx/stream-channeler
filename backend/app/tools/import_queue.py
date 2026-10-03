# TODO: Validate

import multiprocessing
import random
import threading
import uuid
from argparse import ArgumentParser
from collections.abc import Collection

from loguru import logger
from sqlalchemy import Integer
from sqlmodel import Session, col, func

from app.channels.models import ChannelQueue, URLStatus
from app.database import engine, load_models
from app.log import configure_logging, progress_bar
from app.tools.selection import (
    PluginSelection,
    add_selection_arguments,
    add_threads_argument,
    selection_description,
    selection_from_arguments,
)
from app.tools.utils.imports import (
    get_plugin,
    import_one,
    pending_queue_selector,
)
from app.tools.utils.threaded import run_threaded
from plugins.utils.manage_plugins import import_plugins

logger = logger.bind(source="import_queue")

CHUNK_SIZE = 100

QueueKey = tuple[uuid.UUID, str]


# TODO: Validate
def _pending_chunk(
    session: Session,
    selection: PluginSelection,
    passed_over: set[QueueKey],
    process_index: int,
    process_count: int,
) -> list[QueueKey]:
    url_hash = func.hashtext(col(ChannelQueue.url), type_=Integer)
    rows = session.exec(
        pending_queue_selector(
            plugin_keys=selection.plugin_keys,
            user_channels_only=selection.user_channels_only,
        )
        .where(
            (url_hash % process_count + process_count) % process_count == process_index,
        )
        .limit(CHUNK_SIZE + len(passed_over)),
    ).all()
    keys = [
        (item.channel_id, item.url)
        for item in rows
        if (item.channel_id, item.url) not in passed_over
    ]
    return keys[:CHUNK_SIZE]


# TODO: Validate
def _import_queue_key(
    session: Session,
    queue_key: QueueKey,
    plugin_keys: Collection[str],
) -> bool:
    queue_item = session.get(ChannelQueue, queue_key)
    if queue_item is None:
        return True

    plugin_class = get_plugin(queue_item.url, plugin_keys)
    if plugin_class is None:
        if not plugin_keys and queue_item.status == URLStatus.PENDING:
            logger.warning(f"No valid plugin found for URL: {queue_item.url}")
            queue_item.status = URLStatus.FAILED
            queue_item.note = "No valid plugin found."
            session.commit()
            return True
        return False

    import_one(session, queue_item, plugin_class)
    return True


# TODO: Validate
def _import_chunk_threaded(
    chunk: list[QueueKey],
    passed_over: set[QueueKey],
    plugin_keys: Collection[str],
    threads: int,
) -> None:
    remaining = list(chunk)
    random.shuffle(remaining)
    passed_over.update(
        run_threaded(
            remaining,
            lambda session, queue_key: _import_queue_key(
                session,
                queue_key,
                plugin_keys,
            ),
            threads=threads,
            unit="url",
        ),
    )


# TODO: Validate
def _import_chunk(
    session: Session,
    chunk: list[QueueKey],
    passed_over: set[QueueKey],
    plugin_keys: Collection[str],
) -> None:
    with progress_bar(total=len(chunk), unit="url") as progress:
        for queue_key in chunk:
            progress.set_description(queue_key[1])
            if not _import_queue_key(session, queue_key, plugin_keys):
                passed_over.add(queue_key)
            progress.update()


# TODO: Validate
def import_queue(
    session: Session,
    *,
    threads: int = 1,
    selection: PluginSelection | None = None,
    process_index: int = 0,
    process_count: int = 1,
) -> None:
    import_plugins()
    selection = selection or PluginSelection()
    plugin_keys = selection.plugin_keys
    passed_over: set[QueueKey] = set()
    while chunk := _pending_chunk(
        session,
        selection,
        passed_over,
        process_index,
        process_count,
    ):
        if threads > 1:
            _import_chunk_threaded(chunk, passed_over, plugin_keys, threads)
        else:
            _import_chunk(session, chunk, passed_over, plugin_keys)


# TODO: Validate
def run_forever(
    stop_event: threading.Event | None = None,
    *,
    threads: int = 1,
    selection: PluginSelection | None = None,
    process_index: int = 0,
    process_count: int = 1,
) -> None:
    stop_event = stop_event or threading.Event()
    while not stop_event.is_set():
        with Session(engine, expire_on_commit=False) as session:
            import_queue(
                session,
                threads=threads,
                selection=selection,
                process_index=process_index,
                process_count=process_count,
            )
        if stop_event.wait(timeout=60):
            break


# TODO: Validate
def _run_process(
    process_index: int,
    process_count: int,
    threads: int,
    selection: PluginSelection,
) -> None:
    configure_logging()
    load_models()
    run_forever(
        threads=threads,
        selection=selection,
        process_index=process_index,
        process_count=process_count,
    )


# TODO: Validate
def run_processes(
    process_count: int,
    *,
    threads: int,
    selection: PluginSelection,
) -> None:
    context = multiprocessing.get_context("spawn")
    processes = [
        context.Process(
            target=_run_process,
            args=(process_index, process_count, threads, selection),
        )
        for process_index in range(process_count)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join()


if __name__ == "__main__":
    parser = ArgumentParser(description="Import the queued URLs as they come in.")
    add_selection_arguments(parser, include_source=False)
    add_threads_argument(parser)
    parser.add_argument(
        "--processes",
        type=int,
        default=1,
        help="How many processes to split the queue between.",
    )
    arguments = parser.parse_args()
    selected = selection_from_arguments(arguments)

    configure_logging()
    load_models()
    logger.info(
        f"Importing the queue for {selection_description(selected)} "
        f"on {arguments.processes} process{'es' if arguments.processes > 1 else ''} "
        f"of {arguments.threads} thread{'s' if arguments.threads > 1 else ''}",
    )
    if arguments.processes > 1:
        run_processes(
            arguments.processes,
            threads=arguments.threads,
            selection=selected,
        )
    else:
        run_forever(threads=arguments.threads, selection=selected)
    logger.info("Import queue process stopped")
