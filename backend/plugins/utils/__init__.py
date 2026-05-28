# TODO: Validate
"""Plugin utils."""

import logging

from loguru import logger


class _InterceptHandler(logging.Handler):
    """Route standard library logging messages through loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno  # type: ignore[assignment]

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


logging.getLogger("good_ass_pydantic_integrator").addHandler(_InterceptHandler())
