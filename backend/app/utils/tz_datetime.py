# TODO: Validate
"""Timezone-aware datetime functions."""

# ANN401 (Throughout the file) - Any is ok because the actual types are set by
# copy_func_params.

from datetime import UTC, datetime
from typing import Any

from app.utils.copy_params import copy_func_params

_FROMTIMESTAMP_TZ_POSITION = 2
_COMBINE_TZINFO_POSITION = 3
_DATETIME_TZINFO_POSITION = 8


def _local_tz() -> Any:  # noqa: ANN401
    """Return the system's local tzinfo without relying on a naive datetime.now()."""
    return datetime.now(UTC).astimezone().tzinfo


@copy_func_params(datetime.now)
def now(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from time.time()."""
    if not args and "tz" not in kwargs:
        kwargs["tz"] = _local_tz()
    return datetime.now(*args, **kwargs)  # noqa: DTZ005


@copy_func_params(datetime.strptime)
def strptime(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from a string and format."""
    return datetime.strptime(*args, **kwargs).astimezone()


@copy_func_params(datetime.fromtimestamp)
def fromtimestamp(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from a POSIX timestamp."""
    if len(args) < _FROMTIMESTAMP_TZ_POSITION and "tz" not in kwargs:
        kwargs["tz"] = _local_tz()
    return datetime.fromtimestamp(*args, **kwargs)  # noqa: DTZ006


@copy_func_params(datetime.combine)
def combine(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from date and time."""
    if len(args) < _COMBINE_TZINFO_POSITION and "tzinfo" not in kwargs:
        kwargs["tzinfo"] = _local_tz()
    return datetime.combine(*args, **kwargs)


@copy_func_params(datetime.fromisoformat)
def fromisoformat(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from an ISO 8601 timestamp."""
    return datetime.fromisoformat(*args, **kwargs).astimezone()


@copy_func_params(datetime.__init__)
def new(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from year, month, day, etc."""
    if len(args) < _DATETIME_TZINFO_POSITION and "tzinfo" not in kwargs:
        kwargs["tzinfo"] = _local_tz()
    return datetime(*args, **kwargs)  # noqa: DTZ001


# A001 - This function name is copied directly from datetime.min.
def min() -> datetime:  # noqa: A001
    """Get the minimum timezone-aware datetime."""
    return datetime.min.replace(tzinfo=now().tzinfo)


# A001 - This function name is copied directly from datetime.max.
def max() -> datetime:  # noqa: A001
    """Get the maximum timezone-aware datetime."""
    return datetime.max.replace(tzinfo=now().tzinfo)
