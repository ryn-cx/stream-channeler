# TODO: Validate
"""What every other part of the plugin reads an Adult Swim title by."""

from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.AdultSwim.constants import SUBSCRIPTION

if TYPE_CHECKING:
    from pools_closed.show.models import ShowModel


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://adultswim.com/{path.lstrip('/')}"


# TODO: Validate
def show_url(show_key: str) -> str:
    return build_url(f"videos/{show_key}")


# TODO: Validate
def episode_url(show_key: str, episode_slug: str) -> str:
    return build_url(f"videos/{show_key}/{episode_slug}")


# TODO: Validate
def source_requires_auth(source_key: str) -> bool:
    return source_key == SUBSCRIPTION


# TODO: Validate
def season_keys(show: ShowModel) -> list[str]:
    return [str(season.number) for season in show.seasons]


# TODO: Validate
def episode_keys(show: ShowModel, wanted_season_keys: list[str]) -> list[str]:
    return [
        episode.id
        for season in show.seasons
        if str(season.number) in wanted_season_keys
        for episode in season.episodes
    ]


# TODO: Validate
def episode_key_for_slug(show: ShowModel, episode_slug: str) -> str | None:
    for season in show.seasons:
        for episode in season.episodes:
            if episode.slug == episode_slug:
                return episode.id
    return None
