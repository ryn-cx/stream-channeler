# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

from typing import override
from urllib.parse import quote_plus

from plugins.HiDive.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.utils.base_plugin_v2.base import BasePlugin


# TODO: Validate
class UtilsMixin(BasePlugin):
    """The URLs of a title and what its files say about it."""

    # TODO: Validate
    @classmethod
    def _show_url(cls, key: str | int, media_type: str = SERIES_MEDIA_TYPE) -> str:
        if media_type == MOVIE_MEDIA_TYPE:
            return cls.build_url(f"video/{key}")
        return cls.build_url(f"series/{key}")

    # TODO: Validate
    @classmethod
    def _season_url(cls, season_key: str | int) -> str:
        return cls.build_url(f"season/{season_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str | int) -> str:
        return cls.build_url(f"video/{episode_key}")

    # TODO: Validate
    @override
    @classmethod
    def manual_search(cls, query: str) -> str | None:
        return cls.build_url(f"search?q={quote_plus(query)}")
