# TODO: Validate
"""What every other part of the plugin reads a title by."""

from enum import StrEnum
from typing import override
from urllib.parse import quote, quote_plus

from wholoo.episode.models import EpisodeModel
from wholoo.genre.models import GenreModel
from wholoo.genres.models import GenresModel
from wholoo.season.models import SeasonModel

from plugins.utils.base_plugin_v2.base import BasePlugin


# TODO: Validate
class HuluMediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


# TODO: Validate
class UtilsMixin(BasePlugin):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Hulu"

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"

    # TODO: Validate
    @classmethod
    def _show_url(cls, show_key: str, media_type: HuluMediaType) -> str:
        return cls.build_url(f"{media_type}/{show_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    # TODO: Validate
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

    # TODO: Validate
    @staticmethod
    def _season_key(show_key: str, season_number: int) -> str:
        return f"{show_key}:{season_number}"

    # TODO: Validate
    @staticmethod
    def _split_season_key(season_key: str) -> tuple[str, int]:
        show_key, _, season_number = season_key.rpartition(":")
        return show_key, int(season_number)


# TODO: Validate
def season_name(season: SeasonModel) -> str:
    return season.series_grouping_metadata.grouping_name


# TODO: Validate
def series_id(episode: EpisodeModel) -> str:
    """Return the id of the series the episode belongs to."""
    return str(episode.details.vod_items.focus.entity.series_id)


# TODO: Validate
def listed_items(page: GenresModel | GenreModel) -> list[tuple[str, str]]:
    layout = page.props.page_props.layout
    return [
        (item.name, item.href)
        for component in layout.components or []
        if component.type == "list_card"
        for item in component.items or []
        if item.name and item.href
    ]


# TODO: Validate
def media_urls(genre: GenreModel) -> list[str]:
    paths = {
        href: None
        for _name, href in listed_items(genre)
        if href.startswith((f"/{HuluMediaType.MOVIE}/", f"/{HuluMediaType.SERIES}/"))
    }
    return [UtilsMixin.build_url(path) for path in paths]
