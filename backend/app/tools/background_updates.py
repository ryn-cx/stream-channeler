# TODO: Validate
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from app.log import configure_logging
from app.tools import import_queue, update_outdated, update_youtube

logger = logger.bind(source="updater")


# TODO: Validate
def run(stop_event: threading.Event) -> None:
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(update_outdated._update_outdated_forever),
            executor.submit(update_youtube.run_forever),
            executor.submit(import_queue.run_forever, stop_event),
        ]
        for future in as_completed(futures):
            future.result()


# TODO: Validate
def start() -> None:
    threading.Thread(target=run, args=(threading.Event(),), daemon=True).start()


if __name__ == "__main__":
    configure_logging()

    run(threading.Event())
    logger.info("Update process stopped")
