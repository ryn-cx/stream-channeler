# TODO: Validate
"""What the plugin, its importers and its initializer all read Disney+ by."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from plugins.DisneyPlus.constants import ENTITY_URL_REGEX
from plugins.DisneyPlus.files import Entity, SeasonEntity
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kneeminus.entity.models import EntityModel, MainContentItem
    from kneeminus.entity.models import Episode as EntityEpisode
    from kneeminus.entity.models import Season as EntitySeason

    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
def required_value[ValueT](value: ValueT | None, description: str) -> ValueT:
    """Return `value`, raising when the page left it out."""
    if value is None:
        msg = f"The page carries no {description}."
        raise ValueError(msg)
    return value


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://disneyplus.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(entity_id: str) -> str:
    return build_url(f"browse/entity-{entity_id}")


# TODO: Validate
def video_url(episode_id: str) -> str:
    return build_url(f"play/{episode_id}")


# TODO: Validate
def build_season_key(title_key: str, season_id: str) -> str:
    return f"{title_key}:{season_id}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, str]:
    title_key, _, season_id = season_key.partition(":")
    return title_key, season_id


# TODO: Validate
def season_number_from_name(name: str, fallback: int) -> int:
    # Season names are the only place the real season number appears, the
    # position of a season in the list is not reliable because titles can
    # start at a season other than 1.
    if number := re.search(r"\d+", name):
        return int(number.group())
    return fallback


# TODO: Validate
def main_content_item(entity: EntityModel, content_type: str) -> MainContentItem | None:
    """Return the block of the page named by `content_type`, if the page has one."""
    for item in entity.props.page_props.stitch_document.main_content:
        if item.field_type == content_type:
            return item
    return None


# TODO: Validate
def required_main_content_item(
    entity: EntityModel,
    content_type: str,
) -> MainContentItem:
    """Return the block of the page named by `content_type`."""
    item = main_content_item(entity, content_type)
    if item is None:
        msg = f"The page carries no {content_type} block."
        raise ValueError(msg)
    return item


# TODO: Validate
def media_details(entity: EntityModel) -> MainContentItem:
    return required_main_content_item(entity, "MediaDetails")


# TODO: Validate
def hero(entity: EntityModel) -> MainContentItem:
    return required_main_content_item(entity, "DetailEntityHero")


# TODO: Validate
def is_movie(entity: EntityModel) -> bool:
    return main_content_item(entity, "Episodes") is None


# TODO: Validate
def release_year(entity: EntityModel) -> int | None:
    year = hero(entity).release_year
    if year is None:
        return None
    # Disney+ writes a release year as a year on its own or as a range of
    # them, and the year the title came out is the first one either way.
    if match := re.search(r"\d{4}", year):
        return int(match.group())
    return None


# TODO: Validate
def background_image_url(entity: EntityModel) -> str:
    background_image = required_value(
        hero(entity).background_image,
        "background image",
    )
    return background_image.default_image.source


# TODO: Validate
def seasons(entity: EntityModel) -> list[EntitySeason]:
    episodes = main_content_item(entity, "Episodes")
    if episodes is None:
        return []
    return episodes.seasons or []


# TODO: Validate
def season_episodes(season_entity: EntityModel) -> list[EntityEpisode]:
    episodes = main_content_item(season_entity, "Episodes")
    if episodes is None:
        return []
    return episodes.episodes or []


# TODO: Validate
class DisneyPlusShared(BasePlugin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Disney+"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.disneyplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "disneyplus.com"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (ENTITY_URL_REGEX,)

    # TODO: Validate
    def entity_file(self, entity_id: str) -> Entity:
        return self._cached_file(Entity, entity_id)

    # TODO: Validate
    def season_file(self, entity_id: str, season_id: str) -> SeasonEntity:
        return self._cached_file(SeasonEntity, entity_id, season_id)

    # TODO: Validate
    def _url_title_key(self, url: str) -> str:
        if not (match := re.match(self._domains_regex() + ENTITY_URL_REGEX, url)):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        return match.group("title_key")

    # TODO: Validate
    def _entity(self, title_key: str) -> EntityModel:
        return self.entity_file(title_key).parsed()

    # TODO: Validate
    def _media_details(self, title_key: str) -> MainContentItem:
        return media_details(self._entity(title_key))

    # TODO: Validate
    def _background_image_url(self, title_key: str) -> str:
        return background_image_url(self._entity(title_key))

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons.
        return [self.entity_file(title_key)]


# TODO: Validate
class DisneyPlusImporter(DisneyPlusShared, BaseImporter, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        title_key = self._url_title_key(url)
        self.raise_invalid_url_if_no_content(self.entity_file(title_key), url)
        return ParsedURL(title_key)
