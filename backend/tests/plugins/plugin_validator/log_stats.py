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


def _record_best_metrics(
    file_path: Path,
    current_values: dict[str, float],
) -> None:
    best_values: dict[str, float] = {}
    if file_path.exists():
        best_values = json.loads(file_path.read_text())

    updated_values = dict(best_values)
    for metric_name, current_value in current_values.items():
        best_value = best_values.get(metric_name)
        if best_value is None or current_value < best_value:
            updated_values[metric_name] = current_value

    if updated_values != best_values:
        file_path.write_text(json.dumps(updated_values, indent=2))


@contextmanager
def _log_sql_statement_count(
    label: str,
    stats: dict[str, Any],
    stats_directory: Path,
) -> Generator[None]:
    """Log the number of SQL statements executed within the context."""
    stats["sql_statements"] = 0
    stack_traces: list[str] = []

    def count_queries(*_args: object, **_kwargs: object) -> None:
        stats["sql_statements"] += 1

    ignored_path_fragments = (".venv", "AppData", ".vscode")

    def log_queries(*_args: object, **_kwargs: object) -> None:
        stack: list[traceback.FrameSummary] = traceback.extract_stack()
        callers: list[str] = [
            f"{frame.filename}:{frame.lineno} in {frame.name}"
            for frame in stack
            if not any(fragment in frame.filename for fragment in ignored_path_fragments)
            # and "plugin_validator" not in frame.filename
        ]
        # # Commenting code out without ruff errors basically
        # if False:
        callers_str: str = "\n  ".join(callers)
        stack_traces.append(f"SQL #{stats['sql_statements']}\n  {callers_str}")
        logger.info(f"SQL #{stats['sql_statements']}")
        logger.trace(f"Stack trace:\n {callers_str}")

    event.listen(Engine, "before_cursor_execute", count_queries)
    event.listen(Engine, "before_cursor_execute", log_queries)
    try:
        yield
    finally:
        event.remove(Engine, "before_cursor_execute", count_queries)
        event.remove(Engine, "before_cursor_execute", log_queries)
        logger.info(f"SQL statements executed: {stats['sql_statements']} [{label}]")
        (stats_directory / "sql_statements.log").write_text(
            "\n\n".join(stack_traces),
            encoding="utf-8",
        )


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
        _log_sql_statement_count(label, stats, stats_directory),
        _log_execution_time(label, stats),
        _log_memory(stats),
        _log_flamegraph(stats_directory),
    ):
        yield
    _record_best_metrics(
        stats_directory / "stats.json",
        {
            "sql_statements": stats["sql_statements"],
            "peak_memory_bytes": stats["peak_memory_bytes"],
            "execution_time": stats["execution_time"],
        },
    )
