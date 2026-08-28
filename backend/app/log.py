# TODO: Validate
import logging
import sys

from loguru import logger

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
def configure_logging() -> None:
    logger.remove()
    logger.configure(extra={"source": "app"})
    logger.add(sys.stdout, level="INFO", colorize=True, format=_STDOUT_FORMAT)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
