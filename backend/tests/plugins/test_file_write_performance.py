# TODO: Validate
import time
from pathlib import Path
from typing import Any, override

import pyinstrument
from loguru import logger
from sqlmodel import Session

from app.files.models import File
from app.utils import tz_datetime
from plugins.StreamChanneler import StreamChanneler
from plugins.utils.base_plugin.files import JSONFile

PREPOPULATE_COUNT = 10_000
WRITE_COUNT = 50
FLAMEGRAPH_PATH = Path(__file__).parent / "file_write_flamegraph.html"
TEXT_REPORT_PATH = Path(__file__).parent / "file_write_profile.txt"


class PerformanceTestFile(JSONFile[dict[str, Any]]):
    def __init__(self, session: Session, plugin: Any, unique_identifier: str) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return raw


def test_file_write_performance(function_scoped_session: Session) -> None:
    plugin_instance = StreamChanneler(function_scoped_session)
    plugin = plugin_instance.plugin
    content = {"data": "x" * 10_000}

    prepopulate_start = time.perf_counter()
    function_scoped_session.add_all(
        File(
            key=f"Prepopulate/{index}",
            content="x" * 10_000,
            data_timestamp=tz_datetime.now(),
            plugin_id=plugin.id,
        )
        for index in range(PREPOPULATE_COUNT)
    )
    function_scoped_session.commit()
    logger.info(
        f"Pre-populated {PREPOPULATE_COUNT} files in "
        f"{time.perf_counter() - prepopulate_start:.1f}s",
    )

    # Drop all loaded state so plugin.files starts cold, matching a real plugin run
    # against a database that already contains the pre-populated files.
    function_scoped_session.expire_all()

    profiler = pyinstrument.Profiler()
    profiler.start()
    for index in range(WRITE_COUNT):
        file = PerformanceTestFile(function_scoped_session, plugin, str(index))
        start = time.perf_counter()
        file.write(content)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        elapsed = time.perf_counter() - start
        logger.info(f"Write {index} took {elapsed * 1000:.1f}ms")
    profiler.stop()

    FLAMEGRAPH_PATH.write_text(profiler.output_html())
    TEXT_REPORT_PATH.write_text(
        profiler.output_text(unicode=True, color=False),
        encoding="utf-8",
    )
    logger.info(f"Flamegraph written to {FLAMEGRAPH_PATH}")
    logger.info(f"Text profile written to {TEXT_REPORT_PATH}")
