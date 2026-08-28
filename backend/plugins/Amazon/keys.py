# TODO: Validate
"""The ids Amazon writes a title under."""

from __future__ import annotations

import re

from plugins.Amazon.constants import TITLE_KEY_REGEX


# TODO: Validate
def title_key_from_location(location: str) -> str | None:
    # Where the id sits in the address a share link points at.
    found = re.search(rf"/(?:dp|gp/video/detail)/({TITLE_KEY_REGEX})", location)
    if found is None:
        return None
    return found[1]
