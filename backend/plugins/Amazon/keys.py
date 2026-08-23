# TODO: Validate
"""The ids Amazon writes a title under."""

from __future__ import annotations

import re

# A plain ASIN is 10 characters, but a link written by Prime Video itself uses a
# longer id of its own.
TITLE_KEY_REGEX = r"[A-Z0-9]{10,}"

# Where the id sits in the address a share link points at.
REDIRECT_TITLE_KEY = re.compile(rf"/(?:dp|gp/video/detail)/({TITLE_KEY_REGEX})")


# TODO: Validate
def title_key_from_location(location: str) -> str | None:
    found = REDIRECT_TITLE_KEY.search(location)
    if found is None:
        return None
    return found[1]
