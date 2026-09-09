# TODO: Validate
"""What every other part of the plugin reads a Roku title by."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from plugins.Roku.constants import MOVIE_TYPE

if TYPE_CHECKING:
    from nana.content.models import ContentModel
    from nana.content.models import Episode as ContentEpisode
    from nana.content.models import Episode2 as SeasonEpisode


# TODO: Validate
def content_id(value: str | UUID) -> str:
    """Return a Roku content id as the 32 character string the API uses."""
    return value.hex if isinstance(value, UUID) else value


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://therokuchannel.roku.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"details/{title_key}")


# TODO: Validate
def video_url(episode_key: str) -> str:
    return build_url(f"watch/{episode_key}")


# TODO: Validate
def is_movie(content: ContentModel) -> bool:
    content_type = content.type
    if content_type not in (MOVIE_TYPE, "series"):
        msg = f"Invalid media type: {content_type}"
        raise RuntimeError(msg)
    return content_type == MOVIE_TYPE


# TODO: Validate
def build_season_key(title_key: str, season_number: int) -> str:
    return f"{title_key}:{season_number}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    title_key, _, season_number = season_key.rpartition(":")
    return title_key, int(season_number)


# TODO: Validate
def title_episodes(content: ContentModel) -> list[ContentEpisode]:
    return content.episodes or []


# TODO: Validate
def season_numbers(content: ContentModel) -> list[int]:
    numbers: list[int] = []
    for episode in title_episodes(content):
        season_number = int(episode.season_number)
        if season_number not in numbers:
            numbers.append(season_number)
    return numbers


# TODO: Validate
def first_episode_key(content: ContentModel, season_number: int) -> str:
    for episode in title_episodes(content):
        if int(episode.season_number) == season_number:
            return content_id(episode.meta.id)
    msg = f"No episodes for season {season_number}."
    raise ValueError(msg)


# TODO: Validate
def season_episodes(season_content: ContentModel) -> list[SeasonEpisode]:
    season = season_content.season
    if season is None:
        return []
    return season.episodes
