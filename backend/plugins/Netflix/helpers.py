# TODO: Validate
"""The URLs a Netflix title and its episodes are watched at."""

from __future__ import annotations

from plugins.Netflix.files import FileMixin


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
