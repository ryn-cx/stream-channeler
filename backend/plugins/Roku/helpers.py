# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

from typing import override

from plugins.Roku.files import FileMixin


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
    def search_url(cls, query: str) -> str | None:
        return cls.build_url("search")
