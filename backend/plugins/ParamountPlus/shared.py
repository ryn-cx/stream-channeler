# TODO: Validate
"""What the plugin, its importers and its initializer all read Paramount+ by."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.upserter import BaseUpserter

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class ParamountPlusShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return cls.build_url(f"shows/{title_key}/")

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Paramount+"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.paramountplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "paramountplus.com"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @classmethod
    def movie_url(cls, movie_key: str) -> str:
        return cls.build_url(f"movies/video/{movie_key}/")


# TODO: Validate
class ParamountPlusImporter(ParamountPlusShared, BaseUpserter, ABC):
    # TODO: Validate
    @staticmethod
    def build_season_key(title_key: str, season_number: int) -> str:
        return f"{title_key}:{season_number}"

    # TODO: Validate
    @staticmethod
    def split_season_key(season_key: str) -> tuple[str, int]:
        title_key, _, season_number = season_key.rpartition(":")
        return title_key, int(season_number)

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:  # noqa: ARG002
        return []
