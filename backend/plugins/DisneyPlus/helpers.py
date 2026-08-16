# TODO: Validate
"""What every other part of the plugin reads a title by."""

import re
from typing import override

from plugins.DisneyPlus.files import FileMixin

# Season names are the only place the real season number appears, the position of a
# season in the list is not reliable because shows can start at a season other than 1.
_SEASON_NUMBER_REGEX = re.compile(r"\d+")

# Disney+ writes a release year as a year on its own or as a range of them, and
# the year the title came out is the first one either way.
_RELEASE_YEAR_REGEX = re.compile(r"\d{4}")


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and the numbers Disney+ only writes into names."""

    # TODO: Validate
    @staticmethod
    def _season_number_from_name(name: str, fallback: int) -> int:
        if number := _SEASON_NUMBER_REGEX.search(name):
            return int(number.group())
        return fallback

    # TODO: Validate
    def _release_year(self, show_key: str) -> int | None:
        if year := _RELEASE_YEAR_REGEX.search(self._hero(show_key).release_year):
            return int(year.group())
        return None

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
    def search_url(cls, query: str) -> str | None:
        return cls.build_url("browse/search")
