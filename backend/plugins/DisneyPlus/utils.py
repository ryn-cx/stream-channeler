# TODO: Validate
"""What every other part of the plugin reads a Disney+ title by."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kneeminus.entity.models import EntityModel, MainContentItem
    from kneeminus.entity.models import Episode as EntityEpisode
    from kneeminus.entity.models import Season as EntitySeason


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
def search_url() -> str:
    return build_url("browse/search")


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
