# TODO: Validate
"""What each test cost to run, and whether it costs more than it used to."""

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
    from tests.plugins.plugin_validator_v2 import PluginValidatorV2


# How much worse than the best a metric may get before it is reported. Every extra
# query is a regression, where time and memory move about between runs.
_SLOW_RATIOS = {
    "sql_statements": 1.0,
    "execution_time": 1.25,
    "peak_memory_bytes": 1.25,
}


# TODO: Validate
def _load_metrics(file_path: Path) -> dict[str, dict[str, Any]]:
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


# TODO: Validate
def _write_metrics(file_path: Path, all_values: dict[str, dict[str, Any]]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(all_values, indent=2, sort_keys=True),
        encoding="utf-8",
    )


# TODO: Validate
def _slower_metrics(
    best_values: dict[str, float],
    current_values: dict[str, float],
) -> dict[str, dict[str, float]]:
    """Return the metrics that got noticeably worse than their best."""
    slower: dict[str, dict[str, float]] = {}
    for metric_name, current_value in current_values.items():
        best_value = best_values.get(metric_name)
        # A metric with no best, or a best of zero, has nothing to compare against.
        if not best_value:
            continue
        if current_value <= best_value * _SLOW_RATIOS[metric_name]:
            continue
        slower[metric_name] = {
            "best": best_value,
            "current": current_value,
            "increase": current_value - best_value,
            "increase_percent": (current_value - best_value) / best_value * 100,
        }
    return slower


# TODO: Validate
def _record_slow_metrics(
    file_path: Path,
    label: str,
    current_values: dict[str, float],
    slower: dict[str, dict[str, float]],
) -> None:
    """Report the run when it got worse, and drop an old report when it did not."""
    all_values = _load_metrics(file_path)
    if slower:
        all_values[label] = {**current_values, "slower_than_best": slower}
        logger.warning(f"Stats got worse [{label}]: {json.dumps(slower, indent=2)}")
    elif label not in all_values:
        return
    else:
        del all_values[label]

    if all_values:
        _write_metrics(file_path, all_values)
    else:
        file_path.unlink(missing_ok=True)


# TODO: Validate
def _record_best_metrics(
    file_path: Path,
    label: str,
    current_values: dict[str, float],
) -> dict[str, float]:
    """Keep the best value ever recorded for each of `label`'s metrics.

    Every test of a test class shares one file, keyed by the test it belongs to.
    Returns the best values as they were before this run.
    """
    all_values = _load_metrics(file_path)
    best_values: dict[str, float] = all_values.get(label, {})

    updated_values = dict(best_values)
    for metric_name, current_value in current_values.items():
        best_value = best_values.get(metric_name)
        if best_value is None or current_value < best_value:
            updated_values[metric_name] = current_value

    if updated_values != best_values:
        all_values[label] = updated_values
        _write_metrics(file_path, all_values)
    return best_values


# TODO: Validate
@contextmanager
def _log_sql_statement_count(
    label: str,
    stats: dict[str, Any],
    stats_directory: Path,
) -> Generator[None]:
    """Log the number of SQL statements executed within the context."""
    stats["sql_statements"] = 0
    stack_traces: list[str] = []

    # TODO: Validate
    def count_queries(*_args: object, **_kwargs: object) -> None:
        stats["sql_statements"] += 1

    ignored_path_fragments = (".venv", "AppData", ".vscode")

    # TODO: Validate
    def log_queries(*_args: object, **_kwargs: object) -> None:
        stack: list[traceback.FrameSummary] = traceback.extract_stack()
        callers: list[str] = [
            f"{frame.filename}:{frame.lineno} in {frame.name}"
            for frame in stack
            if not any(
                fragment in frame.filename for fragment in ignored_path_fragments
            )
        ]
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


# TODO: Validate
@contextmanager
def _log_execution_time(label: str, stats: dict[str, Any]) -> Generator[None]:
    """Log the execution time within the context."""
    start_time = time.perf_counter()
    yield
    elapsed_time = time.perf_counter() - start_time
    stats["execution_time"] = elapsed_time
    logger.info(f"Execution time: {elapsed_time:.4f}s [{label}]")


# TODO: Validate
@contextmanager
def _log_memory(stats: dict[str, Any]) -> Generator[None]:
    """Log the memory usage within the context."""
    tracemalloc.start()
    yield
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    stats["peak_memory_bytes"] = peak_memory


# TODO: Validate
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


# TODO: Validate
@contextmanager
def log_stats(plugin_validator: PluginValidatorV2[Any]) -> Generator[None]:
    """Combine all of the stats logging into one context manager.

    Held outside whatever the test freezes the clock for, because a frozen clock
    is what the timer reads too and a run measured against one takes no time at
    all.
    """
    label = next(
        frame.function.removeprefix("test_")
        for frame in inspect.stack()
        if frame.function.startswith("test_")
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
    current_values: dict[str, float] = {
        "sql_statements": stats["sql_statements"],
        "peak_memory_bytes": stats["peak_memory_bytes"],
        "execution_time": stats["execution_time"],
    }
    best_values = _record_best_metrics(
        plugin_validator.stats_file_path(),
        label,
        current_values,
    )
    _record_slow_metrics(
        plugin_validator.slow_stats_file_path(),
        label,
        current_values,
        _slower_metrics(best_values, current_values),
    )
