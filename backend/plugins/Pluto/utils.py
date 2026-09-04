# TODO: Validate
"""The URLs of a title and what kind of title it is."""

from typing import override
from urllib.parse import quote

from plugins.Pluto.constants import LOCALE
from plugins.utils.base_plugin_v2.base import BasePlugin


# TODO: Validate
class UtilsMixin(BasePlugin):
    """The URLs Pluto TV writes a title under."""

    # TODO: Validate
    @classmethod
    def _series_url(cls, show_key: str) -> str:
        return cls.build_url(f"{LOCALE}/on-demand/series/{show_key}/details")

    # TODO: Validate
    @classmethod
    def _movie_url(cls, show_key: str) -> str:
        return cls.build_url(f"{LOCALE}/on-demand/movies/{show_key}/details")

    # TODO: Validate
    @classmethod
    def _season_url(cls, show_key: str, season_number: int) -> str:
        return cls.build_url(
            f"{LOCALE}/on-demand/series/{show_key}/season/{season_number}",
        )

    # TODO: Validate
    @classmethod
    def _episode_url(
        cls,
        show_key: str,
        season_number: int,
        episode_key: str,
    ) -> str:
        return cls.build_url(
            f"{LOCALE}/on-demand/series/{show_key}/season/{season_number}"
            f"/episode/{episode_key}",
        )

    # TODO: Validate
    @override
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return cls.build_url(f"{LOCALE}/search?query={quote(query)}")
