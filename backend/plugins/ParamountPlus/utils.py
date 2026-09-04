# TODO: Validate
"""What every other part of the plugin reads a title by."""

from typing import override

from plugins.utils.base_plugin_v2.base import BasePlugin


# TODO: Validate
class UtilsMixin(BasePlugin):
    """The URLs of a title and whether it is a film or a series."""

    # TODO: Validate
    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"shows/{show_key}/")

    # TODO: Validate
    @classmethod
    def _movie_url(cls, movie_key: str) -> str:
        return cls.build_url(f"movies/video/{movie_key}/")

    # TODO: Validate
    @override
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return cls.build_url("search/")
