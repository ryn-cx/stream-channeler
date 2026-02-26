# TODO: Validate
"""Timezone-aware datetime functions."""

# ANN401 (Throughout the file) - Any is ok because the actual types are set by
# copy_func_params.

from datetime import datetime
from typing import Any

from app.utils.copy_params import copy_func_params


@copy_func_params(datetime.now)
def now(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from time.time()."""
    return datetime.now(*args, **kwargs).astimezone()


@copy_func_params(datetime.strptime)
def strptime(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from a string and format."""
    return datetime.strptime(*args, **kwargs).astimezone()


@copy_func_params(datetime.fromtimestamp)
def fromtimestamp(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from a POSIX timestamp."""
    return datetime.fromtimestamp(*args, **kwargs).astimezone()


@copy_func_params(datetime.combine)
def combine(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from date and time."""
    return datetime.combine(*args, **kwargs).astimezone()


@copy_func_params(datetime.fromisoformat)
def fromisotimestamp(*args: Any, **kwargs: Any) -> datetime:  # noqa: ANN401
    """Construct a timezone-aware datetime from an ISO 8601 timestamp."""
    return datetime.fromisoformat(*args, **kwargs).astimezone()


# A001 - This function name is copied directly from datetime.min.
def min() -> datetime:  # noqa: A001
    """Get the minimum timezone-aware datetime."""
    return datetime.min.replace(tzinfo=now().tzinfo)
