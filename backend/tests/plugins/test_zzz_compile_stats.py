# TODO: Validate
import csv
import json
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.constants import TEST_FILES_FOLDER

STAT_KEYS = ["sql_statements", "execution_time", "peak_memory_bytes"]


def compile_stats() -> list[dict[str, str]]:
    """Collect all stats from test folders into a list of dictionaries."""
    rows: list[dict[str, str]] = []

    for plugin_folder in sorted(TEST_FILES_FOLDER.iterdir()):
        if not plugin_folder.is_dir():
            continue

        for test_class_folder in sorted(plugin_folder.iterdir()):
            if not test_class_folder.is_dir():
                continue

            stats_folder = test_class_folder / "stats"
            if not stats_folder.exists():
                continue

            for label_folder in sorted(stats_folder.iterdir()):
                if not label_folder.is_dir():
                    continue

                stats_file = label_folder / "stats.json"
                if not stats_file.exists():
                    continue

                stats = json.loads(stats_file.read_text())
                row: dict[str, str] = {
                    "plugin": plugin_folder.name,
                    "test_class": test_class_folder.name,
                    "label": label_folder.name,
                }
                for stat_key in STAT_KEYS:
                    row[stat_key] = str(stats.get(stat_key, ""))

                rows.append(row)

    # Sort by execution time descending (slowest first)
    rows.sort(key=lambda r: float(r.get("execution_time") or 0), reverse=True)
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    """Write the collected stats to a CSV file."""
    headers = ["plugin", "test_class", "label", *STAT_KEYS]

    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_compile_stats() -> None:
    """Compile stats from test runs into a CSV file."""
    rows = compile_stats()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = TEST_FILES_FOLDER / f"compiled_stats_{timestamp}.csv"
    write_csv(rows, output_path)
    logger.info(f"Compiled stats written to {output_path}")
