# TODO: Validate
"""What the plugin, its importers and its initializer all read HBO Max by."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from plugins.HBOMax.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.upserter import BaseUpserter

if TYPE_CHECKING:
    from minbo.movie.models import ParsedMovieModel
    from minbo.show.models import ParsedShowModel


# TODO: Validate
class HBOMaxShared(BasePluginCore):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HBO Max"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hbomax.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domains(cls) -> list[str]:
        return ["play.hbomax.com", "hbomax.com"]

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TITLE_URL_REGEX)


# TODO: Validate
class HBOMaxImporter(HBOMaxShared, BaseUpserter, ABC):
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
    @classmethod
    def related_urls(cls, page: ParsedShowModel | ParsedMovieModel) -> list[str]:
        urls: dict[str, None] = {
            listed_title.url: None for listed_title in page.related if listed_title.url
        }
        urls.update(cls._carousel_urls(page, site_wide=False))
        return list(urls)

    # TODO: Validate
    @classmethod
    def page_urls(cls, page: ParsedShowModel | ParsedMovieModel) -> list[str]:
        urls: dict[str, None] = dict.fromkeys(cls.related_urls(page))
        urls.update(cls._carousel_urls(page, site_wide=True))
        return list(urls)

    # TODO: Validate
    @staticmethod
    def _carousel_urls(
        page: ParsedShowModel | ParsedMovieModel,
        *,
        site_wide: bool,
    ) -> dict[str, None]:
        return {
            listed_title.url: None
            for carousel in page.carousels
            if (carousel.collection_id in ("13187", "14196")) == site_wide
            for listed_title in carousel.titles
            if listed_title.url
        }
