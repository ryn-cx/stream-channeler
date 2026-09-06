# TODO: Validate
"""What every other part of the plugin reads a HiDive title by."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from plugins.HiDive.constants import (
    MOVIE_MEDIA_TYPE,
    RELEASE_DATE_PREFIX,
    SERIES_MEDIA_TYPE,
)

if TYPE_CHECKING:
    from diving_board.schedule import models as schedule_models
    from diving_board.season import models as season_models
    from diving_board.series import models as series_models
    from diving_board.vod import models as vod_models


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://hidive.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(key: str | int, media_type: str = SERIES_MEDIA_TYPE) -> str:
    if media_type == MOVIE_MEDIA_TYPE:
        return build_url(f"video/{key}")
    return build_url(f"series/{key}")


# TODO: Validate
def season_url(season_key: str | int) -> str:
    return build_url(f"season/{season_key}")


# TODO: Validate
def episode_url(episode_key: str | int) -> str:
    return build_url(f"video/{episode_key}")


# TODO: Validate
def search_url(query: str) -> str:
    return build_url(f"search?q={quote_plus(query)}")


# TODO: Validate
def single_element[ElementT](elements: list[ElementT], description: str) -> ElementT:
    if not elements:
        msg = f"No {description} element found"
        raise ValueError(msg)
    if len(elements) > 1:
        msg = f"Too many {description} elements found"
        raise ValueError(msg)
    return elements[0]


# TODO: Validate
def vod_hero(vod_data: vod_models.VodModel) -> vod_models.Element:
    """Return the hero element of a parsed vod file."""
    return single_element(
        [element for element in vod_data.elements if element.field_type == "hero"],
        "hero",
    )


# TODO: Validate
def season_hero(season_data: season_models.SeasonModel) -> season_models.Element:
    """Return the hero element of a parsed season file."""
    return single_element(
        [element for element in season_data.elements if element.field_type == "hero"],
        "hero",
    )


# TODO: Validate
def schedule_group_list(
    schedule_data: schedule_models.ScheduleModel,
) -> schedule_models.Element:
    """Return the element a page of the schedule lists its days in."""
    return single_element(
        [
            element
            for element in schedule_data.elements
            if element.field_type == "groupList"
        ],
        "groupList",
    )


# TODO: Validate
def season_bucket(season_data: season_models.SeasonModel) -> season_models.Element:
    """Return the element a season's own episodes are listed in."""
    return single_element(
        [
            element
            for element in season_data.elements
            if element.field_type == "bucket" and element.attributes.type == "season"
        ],
        "'season' bucket",
    )


# TODO: Validate
def series_image_url(series_data: series_models.SeriesModel) -> str:
    """Return the hero image URL from a parsed series file."""
    for element in series_data.elements:
        if element.attributes.image:
            return element.attributes.image.attributes.source
    msg = "No image element found in series file."
    raise ValueError(msg)


# TODO: Validate
def hero_image_url(hero: season_models.Element | vod_models.Element) -> str:
    """Return the image URL a hero is illustrated with."""
    if not hero.attributes.image:
        msg = "No image found in hero element."
        raise ValueError(msg)
    return hero.attributes.image.attributes.source


# TODO: Validate
def movie_title(hero: vod_models.Element) -> str:
    """Return the movie's title from the VOD's own hero action."""
    for action in hero.attributes.actions or []:
        data = action.attributes.action.data
        if data.type == "VOD":
            return data.title
    msg = "No VOD action found in movie hero."
    raise ValueError(msg)


# TODO: Validate
def movie_description(hero: vod_models.Element) -> str | None:
    """Return the movie's synopsis from the first hero content block with text."""
    for content in hero.attributes.content or []:
        if content.attributes.text:
            return content.attributes.text
    return None


# TODO: Validate
def tag_text(tag: vod_models.Tag) -> str | None:
    text = tag.attributes.text
    if text is None or isinstance(text, str):
        return text
    return text.attributes.text


# TODO: Validate
def release_date(hero: vod_models.Element) -> datetime | None:
    """Return the day the title came out, as its hero's tags give it."""
    for content in hero.attributes.content or []:
        for tag in content.attributes.tags or []:
            text = tag_text(tag)
            if text and text.startswith(RELEASE_DATE_PREFIX):
                date_string = text.removeprefix(RELEASE_DATE_PREFIX)
                return datetime.strptime(date_string, "%B %d, %Y").astimezone()
    return None


# TODO: Validate
def movie_duration(hero: vod_models.Element) -> int | None:
    """Return how long the movie runs for, in seconds."""
    for content in hero.attributes.content or []:
        if content.attributes.duration is not None:
            return content.attributes.duration
    return None


# TODO: Validate
def series_season_items(
    series_data: series_models.SeriesModel,
) -> list[series_models.Item1]:
    """Return the list of seasons from a parsed series file."""
    for element in series_data.elements:
        if element.attributes.seasons:
            return element.attributes.seasons.items
    msg = "No seasons element found in series file."
    raise ValueError(msg)


# TODO: Validate
def episode_number(title: str | None) -> int | None:
    # TODO: Double check there really is no better way to get this information.
    # HiDive puts the episode number as an E## prefix in the title.
    match = re.match(r"^E(\d+)", title) if title else None
    return int(match.group(1)) if match else None


# TODO: Validate
def element_text(element: schedule_models.Element2) -> str:
    """Return the text a card's element is written with."""
    text = element.attributes.text
    if not isinstance(text, str):
        msg = "Schedule card element has no text."
        raise TypeError(msg)
    return text


# TODO: Validate
def element_release_date(element: schedule_models.Element2) -> datetime:
    """Return the day a card's element says the release is on."""
    text = element.attributes.text
    if not isinstance(text, datetime):
        msg = "Schedule card element has no release date."
        raise TypeError(msg)
    return text.astimezone()


# TODO: Validate
def card_title_name(text: str) -> str:
    """Return the title a card is for, out of the "S1 E2 - Title Name" it is titled."""
    _episode_number, separator, title_name = text.partition(" - ")
    if not separator:
        msg = f"Schedule card title has no title name: {text}"
        raise ValueError(msg)
    return title_name
