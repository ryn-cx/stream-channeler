# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Roku.constants import MOVIE_TYPE
from plugins.Roku.files import FileMixin
from plugins.utils.abstract_plugin import PluginShowIdentity


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and the pages it is watched from."""

    # TODO: Validate
    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"details/{show_key}")

    # TODO: Validate
    @classmethod
    def _video_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    # TODO: Validate
    @override
    @classmethod
    def manual_search(cls, query: str) -> str | None:
        return cls.build_url("search")

    # TODO: Validate
    @override
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        content_file = self.content_file(show_key)
        content_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        content = content_file.parsed()
        return PluginShowIdentity(
            title=content.title,
            media_type="Movie" if content.type == MOVIE_TYPE else "TV Show",
            year=content.release_year,
        )
