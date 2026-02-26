# TODO: Validate
import csv
from pathlib import Path

from loguru import logger

from app.constants import TEST_FILES_FOLDER

STAT_FILES = ["lazy_loads", "sql_statements", "execution_time"]


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

                row: dict[str, str] = {
                    "plugin": plugin_folder.name,
                    "test_class": test_class_folder.name,
                    "label": label_folder.name,
                }

                for stat_name in STAT_FILES:
                    stat_file = label_folder / f"{stat_name}.txt"
                    if stat_file.exists():
                        row[stat_name] = stat_file.read_text().strip()
                    else:
                        row[stat_name] = ""

                rows.append(row)

    # Sort by execution time descending (slowest first)
    rows.sort(key=lambda r: float(r.get("execution_time") or 0), reverse=True)
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    """Write the collected stats to a CSV file."""
    headers = ["plugin", "test_class", "label", *STAT_FILES]

    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_compile_stats() -> None:
    """Compile stats from test runs into a CSV file."""
    rows = compile_stats()
    output_path = TEST_FILES_FOLDER / "compiled_stats.csv"
    write_csv(rows, output_path)
    logger.info(f"Compiled stats written to {output_path}")
