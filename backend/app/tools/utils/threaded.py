# TODO: Validate

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlmodel import Session

from app.database import engine
from app.log import progress_bar


# TODO: Validate
def run_threaded[KeyT](
    keys: list[KeyT],
    handle: Callable[[Session, KeyT], bool],
    *,
    threads: int,
    unit: str,
) -> set[KeyT]:
    remaining = list(keys)
    unfinished: set[KeyT] = set()
    taken = threading.Lock()
    progress_lock = threading.Lock()

    with (
        progress_bar(total=len(remaining), unit=unit) as progress,
        ThreadPoolExecutor(max_workers=threads) as executor,
    ):
        # TODO: Validate
        def worker() -> None:
            with Session(engine, expire_on_commit=False) as session:
                while True:
                    with taken:
                        if not remaining:
                            return
                        key = remaining.pop()

                    if not handle(session, key):
                        with taken:
                            unfinished.add(key)
                    with progress_lock:
                        progress.update()

        futures = [executor.submit(worker) for _ in range(threads)]
        for future in as_completed(futures):
            future.result()

    return unfinished
