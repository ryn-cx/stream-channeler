# TODO: Validate
import logging
import sys
from collections.abc import Iterable
from typing import Any

from loguru import logger
from tqdm import tqdm

_STDOUT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "source=<cyan>{extra[source]}</cyan> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)


# TODO: Validate
class InterceptHandler(logging.Handler):
    # TODO: Validate
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.bind(source=record.name).opt(
            depth=depth,
            exception=record.exc_info,
        ).log(level, record.getMessage())


# TODO: Validate
def _tqdm_sink(message: str) -> None:
    with tqdm.external_write_mode(file=sys.stderr):
        sys.stderr.write(message)
        sys.stderr.flush()


# TODO: Validate
def progress_bar(
    iterable: Iterable[Any] | None = None,
    *,
    total: int | None = None,
    unit: str,
) -> tqdm[Any]:
    return tqdm(
        iterable,
        total=total,
        unit=unit,
        file=sys.stderr,
        disable=None,
        ascii=True,
        ncols=80,
    )


# TODO: Validate
def configure_logging() -> None:
    logger.remove()
    logger.configure(extra={"source": "app"})
    logger.add(
        _tqdm_sink,
        level="INFO",
        colorize=True,
        format=_STDOUT_FORMAT,
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    logging.captureWarnings(capture=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
