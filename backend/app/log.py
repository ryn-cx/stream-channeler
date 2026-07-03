# TODO: Validate
import sys

from loguru import logger

_STDOUT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "source=<cyan>{extra[source]}</cyan> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)


def configure_logging() -> None:  # noqa: D103
    logger.remove()
    logger.configure(extra={"source": "app"})
    logger.add(sys.stdout, level="INFO", colorize=True, format=_STDOUT_FORMAT)
