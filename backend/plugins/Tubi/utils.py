# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import override
from urllib.parse import quote

from app.utils import tz_datetime
from plugins.Tubi.files import FileMixin
from plugins.utils.abstract_plugin import PluginShowIdentity


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and the values read straight off its content file."""

    # TODO: Validate
    @staticmethod
    def _episode_name(title: str) -> str:
        # Episode titles are prefixed with their season and episode number,
        # e.g. "S01:E01 - What a Night for a Knight".
        return re.sub(r"^S\d+:E\d+ - ", "", title)

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
    def manual_search(cls, query: str) -> str | None:
        return cls.build_url(f"search/{quote(query)}")

    # TODO: Validate
    @override
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        content_file = self.content_file(show_key)
        content_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        content = content_file.parsed()
        return PluginShowIdentity(
            title=content.title,
            media_type="Movie" if self._is_movie(show_key) else "Series",
            year=content.year,
        )
