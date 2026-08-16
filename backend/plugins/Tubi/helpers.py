# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

import re
from typing import override
from urllib.parse import quote

from plugins.Tubi.files import FileMixin

# Episode titles are prefixed with their season and episode number, e.g.
# "S01:E01 - What a Night for a Knight".
_EPISODE_TITLE_PREFIX_REGEX = re.compile(r"^S\d+:E\d+ - ")


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and the values read straight off its content file."""

    # TODO: Validate
    @staticmethod
    def _episode_name(title: str) -> str:
        return _EPISODE_TITLE_PREFIX_REGEX.sub("", title)

    # TODO: Validate
    @staticmethod
    def _first_image(images: list[str]) -> str | None:
        return images[0] if images else None

    # TODO: Validate
    @classmethod
    def _series_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    # TODO: Validate
    @classmethod
    def _movie_url(cls, show_key: str) -> str:
        return cls.build_url(f"movies/{show_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"tv-shows/{episode_key}")

    # TODO: Validate
    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"search/{quote(query)}")
