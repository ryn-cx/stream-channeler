# TODO: Validate
"""What every other part of the plugin reads a title by."""

from enum import StrEnum
from typing import override
from urllib.parse import quote, quote_plus

from plugins.utils.base_plugin_v2.base import PluginBase


# TODO: Validate
class HuluMediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


# TODO: Validate
class UtilsMixin(PluginBase):
    """The URLs of a title and what a search result of it is asked for by."""

    # TODO: Validate
    @classmethod
    def _show_url(cls, show_key: str, media_type: HuluMediaType) -> str:
        return cls.build_url(f"{media_type}/{show_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    # TODO: Validate
    @override
    @classmethod
    def manual_search(cls, query: str) -> str | None:
        return cls.build_url(f"search?q={quote_plus(query)}")

    # TODO: Validate
    @staticmethod
    def _image_url(path: str) -> str:
        operations = quote('[{"resize":"1920x1920|max"},{"format":"webp"}]', safe=":,")
        return f"{path}&operations={operations}"

    # TODO: Validate
    @staticmethod
    def _thumbnail_url(path: str) -> str:
        operations = quote('[{"resize":"480x480|max"},{"format":"webp"}]', safe=":,")
        return f"{path}&operations={operations}"
