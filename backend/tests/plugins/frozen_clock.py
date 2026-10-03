# TODO: Validate
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, tzinfo
from unittest.mock import patch

from app.utils import tz_datetime

DEFAULT_TIME = datetime(2026, 1, 1, tzinfo=UTC)


# TODO: Validate
@contextmanager
def frozen_clock(moment: datetime = DEFAULT_TIME) -> Generator[None]:
    # TODO: Validate
    def _now(tz: tzinfo | None = None) -> datetime:
        return moment.astimezone(tz)

    with patch.object(tz_datetime, "now", _now):
        yield
