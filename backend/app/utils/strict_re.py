# TODO: Validate
"""Strict regex matching functions."""

import re
from typing import Any

from app.utils.copy_params import copy_func_params


# ANN401 Any is ok because the actual types are set by the copy_func_params.
@copy_func_params(re.match)
def strict_match(
    pattern: str | re.Pattern[str],
    string: str,
    *args: Any,  # noqa: ANN401
    **kwargs: Any,  # noqa: ANN401
) -> re.Match[str]:
    """Find a regex match or raise an error if no match is found."""
    match = re.match(pattern, string, *args, **kwargs)
    if not match:
        msg = (
            "Expected a match, but no match was found",
            f"\n\tPattern: {pattern}",
            f"\n\tString: {string}",
        )
        raise ValueError(msg)
    return match


def strict_group(match: re.Match[str], group: int | str) -> str:
    """Get a regex group from a match or raise an error if the group is not found."""
    result = match.group(group)
    if result is None:
        msg = (
            "Expected a group value, but none was found",
            f"\n\tMatch: {match.re.pattern}",
            f"\n\tGroup: {group}",
        )
        raise ValueError(msg)
    return result
