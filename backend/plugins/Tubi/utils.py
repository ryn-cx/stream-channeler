# TODO: Validate
"""What every other part of the plugin reads a Tubi title by."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from plugi.content.models import Child as SeasonChild
    from plugi.content.models import Child1 as EpisodeChild
    from plugi.content.models import ContentModel


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://tubitv.com/{path.lstrip('/')}"


# TODO: Validate
def series_url(title_key: str) -> str:
    return build_url(f"series/{title_key}")


# TODO: Validate
def movie_url(title_key: str) -> str:
    return build_url(f"movies/{title_key}")


# TODO: Validate
def episode_url(episode_key: str) -> str:
    return build_url(f"tv-shows/{episode_key}")


# TODO: Validate
def search_url(query: str) -> str:
    return build_url(f"search/{quote(query)}")


# TODO: Validate
def episode_name(title: str) -> str:
    # Episode titles are prefixed with their season and episode number,
    # e.g. "S01:E01 - What a Night for a Knight".
    return re.sub(r"^S\d+:E\d+ - ", "", title)


# TODO: Validate
def first_image(images: list[str]) -> str | None:
    return images[0] if images else None


# TODO: Validate
def is_movie(content: ContentModel) -> bool:
    # The `type` field of a Tubi content response marks a series; a movie
    # and a single episode both use "v".
    return content.type != "s"


# TODO: Validate
def build_season_key(title_key: str, season_id: str) -> str:
    """Encode the title key into the season key.

    Every entity's data comes from the single content file keyed by the title,
    but the base plugin resolves episode files from a season key alone, so the
    title key is carried inside it.
    """
    return f"{title_key}:{season_id}"


# TODO: Validate
def movie_season_key(title_key: str) -> str:
    # A movie has no seasons of its own so its single season is given a
    # fixed id.
    return build_season_key(title_key, "0")


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, str]:
    title_key, _, season_id = season_key.partition(":")
    return title_key, season_id


# TODO: Validate
def seasons(content: ContentModel) -> list[SeasonChild]:
    children = content.children
    if children is None:
        return []
    # Tubi returns the seasons in an arbitrary order.
    return sorted(children, key=lambda season: int(season.id))


# TODO: Validate
def season_episodes(content: ContentModel, season_id: str) -> list[EpisodeChild]:
    for season in seasons(content):
        if season.id == season_id:
            return season.children
    return []
