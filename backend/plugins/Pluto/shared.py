# TODO: Validate
"""What the plugin, its importers and its initializer all read Pluto TV by."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, override

from plugins.Pluto.constants import (
    LOCALE,
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    SHOW_URL_REGEX,
)
from plugins.Pluto.files import ItemsFile
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.upserter import BaseUpserter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from notaplanet.items.models import Cover as ItemCover
    from notaplanet.seasons.models import Cover as SeasonCover

    from app.titles.models import Title


# TODO: Validate
class PlutoShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Pluto TV"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://pluto.tv/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "pluto.tv"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, SERIES_URL_REGEX, SHOW_URL_REGEX)

    # TODO: Validate
    @classmethod
    def series_url(cls, title_key: str) -> str:
        return cls.build_url(f"{LOCALE}/on-demand/series/{title_key}/details")

    # TODO: Validate
    @classmethod
    def movie_url(cls, title_key: str) -> str:
        return cls.build_url(f"{LOCALE}/on-demand/movies/{title_key}/details")


# TODO: Validate
class PlutoImporter(PlutoShared, BaseUpserter, ABC):
    # TODO: Validate
    @staticmethod
    def build_season_key(title_key: str, season_number: int) -> str:
        """Encode the title key into the season key.

        Every entity's data comes from the single file keyed by the title, but the
        base plugin resolves episode files from a season key alone, so the title
        key is included inside it.
        """
        return f"{title_key}:{season_number}"

    # TODO: Validate
    @staticmethod
    def split_season_key(season_key: str) -> tuple[str, int]:
        title_key, _, season_number = season_key.partition(":")
        return title_key, int(season_number)

    # TODO: Validate
    def items_file(self, item_id: str) -> ItemsFile:
        return self._cached_file(ItemsFile, item_id)

    # TODO: Validate
    @staticmethod
    def _cover_ratio(cover: ItemCover | SeasonCover) -> float:
        width, _, height = cover.aspect_ratio.partition(":")
        return float(width) / float(height)

    # TODO: Validate
    @classmethod
    def poster_url(cls, covers: Sequence[ItemCover | SeasonCover]) -> str | None:
        portrait = [cover for cover in covers if cls._cover_ratio(cover) < 1]
        return min(portrait, key=cls._cover_ratio).url if portrait else None

    # TODO: Validate
    @abstractmethod
    def _media_type_channel_key(self) -> str: ...

    # TODO: Validate
    @abstractmethod
    def _genre(self, title_key: str) -> str: ...

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:
            msg = "Title.url is not set."
            raise AttributeError(msg)

        self.add_title_to_channel("All Titles", title)
        self.set_title_tag_channels(
            title,
            [self._media_type_channel_key(), self._genre(title.key)],
        )
