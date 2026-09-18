# TODO: Validate
"""The ids Amazon writes a title under."""

from __future__ import annotations

import re

from plugins.Amazon.constants import LINK_ID_REGEX


# TODO: Validate
def link_id_from_location(location: str) -> str | None:
    found = re.search(rf"/(?:dp|gp/video/detail)/({LINK_ID_REGEX})", location)
    if found is None:
        return None
    return found[1]
