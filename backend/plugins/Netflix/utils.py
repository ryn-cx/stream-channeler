# TODO: Validate
"""The URLs a Netflix title and its episodes are watched at."""

from __future__ import annotations

from datetime import timedelta
from typing import override
from urllib.parse import quote_plus

from app.utils import tz_datetime
from plugins.Netflix.files import FileMixin
from plugins.utils.abstract_plugin import PluginShowIdentity


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and of the episodes under it."""

    # TODO: Validate
    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"title/{show_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    # TODO: Validate
    @classmethod
    @override
    def manual_search(cls, query: str) -> str:
        return cls.build_url(f"search?q={quote_plus(query)}")

    # TODO: Validate
    @override
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        self.title_file(show_key).download_if_outdated(
            tz_datetime.now() - timedelta(days=7),
        )
        video = self._title_video(show_key)
        return PluginShowIdentity(
            title=video.title,
            media_type="Movie" if self._is_movie(show_key) else "TV Show",
            year=video.latest_year,
        )
