# TODO: Validate
"""What every other part of the plugin reads a Paramount+ title by."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX

if TYPE_CHECKING:
    from trivial_minus.show.models import ShowModel


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://paramountplus.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"shows/{title_key}/")


# TODO: Validate
def movie_url(movie_key: str) -> str:
    return build_url(f"movies/video/{movie_key}/")


# TODO: Validate
def build_season_key(title_key: str, season_number: int) -> str:
    return f"{title_key}:{season_number}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    title_key, _, season_number = season_key.rpartition(":")
    return title_key, int(season_number)


# TODO: Validate
def related_urls(show: ShowModel) -> list[str]:
    urls: dict[str, None] = {}
    for recommendation in show.recommendations:
        if match := re.match(MOVIE_URL_REGEX, recommendation.url):
            urls[movie_url(match.group("title_key"))] = None
        elif (match := re.match(TITLE_URL_REGEX, recommendation.url)) and (
            match.group("title_key") != "video"
        ):
            urls[title_url(match.group("title_key"))] = None
    return list(urls)
