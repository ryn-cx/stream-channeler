# TODO: Validate


import inspect
import json
import time
import traceback
import tracemalloc
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyinstrument
from loguru import logger
from sqlalchemy import Engine, event

if TYPE_CHECKING:
    from tests.plugins.plugin_validator import PluginValidator


@contextmanager
def _log_sql_statement_count(label: str, stats: dict[str, Any]) -> Generator[None]:
    """Log the number of SQL statements executed within the context."""
    stats["sql_statements"] = 0

    def count_queries(*_args: object, **_kwargs: object) -> None:
        stats["sql_statements"] += 1

    def log_queries(*_args: object, **_kwargs: object) -> None:
        stack: list[traceback.FrameSummary] = traceback.extract_stack()
        callers: list[str] = [
            f"{frame.filename}:{frame.lineno} in {frame.name}"
            for frame in stack
            if ".venv" not in frame.filename
            # and "plugin_validator" not in frame.filename
        ]
        callers_str: str = "\n  ".join(callers)

        # logger.info(f"SQL #{stats['sql_statements']}")
        # logger.trace(f"Stack trace:\n {callers_str}")

    event.listen(Engine, "before_cursor_execute", count_queries)
    event.listen(Engine, "before_cursor_execute", log_queries)
    yield
    event.remove(Engine, "before_cursor_execute", count_queries)
    event.remove(Engine, "before_cursor_execute", log_queries)
    logger.info(f"SQL statements executed: {stats['sql_statements']} [{label}]")


@contextmanager
def _log_execution_time(label: str, stats: dict[str, Any]) -> Generator[None]:
    """Log the execution time within the context."""
    start_time = time.perf_counter()
    yield
    elapsed_time = time.perf_counter() - start_time
    stats["execution_time"] = elapsed_time
    logger.info(f"Execution time: {elapsed_time:.4f}s [{label}]")


@contextmanager
def _log_memory(stats: dict[str, Any]) -> Generator[None]:
    """Log the memory usage within the context."""
    tracemalloc.start()
    yield
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    stats["peak_memory_bytes"] = peak_memory


@contextmanager
def _log_flamegraph(stats_directory: Path) -> Generator[None]:
    """Generate an HTML flamegraph for the code executed within the context."""
    profiler = pyinstrument.Profiler()
    profiler.start()
    try:
        yield
    finally:
        profiler.stop()
        flamegraph_path = stats_directory / "flamegraph.html"
        flamegraph_path.write_text(profiler.output_html())


@contextmanager
def log_stats(plugin_validator: PluginValidator[Any]) -> Generator[None]:
    """Combined context manager for all stats logging."""
    label = next(
        fi.function.removeprefix("test_")
        for fi in inspect.stack()
        if fi.function.startswith("test_")
    )

    stats_directory = plugin_validator.stats_directory_path(label)
    stats_directory.mkdir(parents=True, exist_ok=True)

    stats: dict[str, Any] = {}
    with (
        _log_sql_statement_count(label, stats),
        _log_execution_time(label, stats),
        _log_memory(stats),
        _log_flamegraph(stats_directory),
    ):
        yield
    stats_file_path = stats_directory / "stats.json"
    stats_file_path.write_text(json.dumps(stats, indent=2))
