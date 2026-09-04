# TODO: Validate
"""What every other part of the plugin reads a title by."""

import re
from typing import override

from plugins.utils.base_plugin_v2.base import BasePlugin


# TODO: Validate
def required_value[ValueT](value: ValueT | None, description: str) -> ValueT:
    """Return `value`, raising when the page left it out."""
    if value is None:
        msg = f"The page carries no {description}."
        raise ValueError(msg)
    return value


# TODO: Validate
class UtilsMixin(BasePlugin):
    """The URLs of a title and the numbers Disney+ only writes into names."""

    # TODO: Validate
    @staticmethod
    def _season_number_from_name(name: str, fallback: int) -> int:
        # Season names are the only place the real season number appears, the
        # position of a season in the list is not reliable because shows can
        # start at a season other than 1.
        if number := re.search(r"\d+", name):
            return int(number.group())
        return fallback

    # TODO: Validate
    @classmethod
    def _show_url(cls, entity_id: str) -> str:
        return cls.build_url(f"browse/entity-{entity_id}")

    # TODO: Validate
    @classmethod
    def _video_url(cls, episode_id: str) -> str:
        return cls.build_url(f"play/{episode_id}")

    # TODO: Validate
    @override
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return cls.build_url("browse/search")
