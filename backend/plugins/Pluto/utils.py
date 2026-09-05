# TODO: Validate
"""What every other part of the plugin reads a Pluto TV title by."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

from plugins.Pluto.constants import LOCALE

if TYPE_CHECKING:
    from notaplanet.seasons.models import Episode, Season, SeasonsModel


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://pluto.tv/{path.lstrip('/')}"


# TODO: Validate
def series_url(show_key: str) -> str:
    return build_url(f"{LOCALE}/on-demand/series/{show_key}/details")


# TODO: Validate
def movie_url(show_key: str) -> str:
    return build_url(f"{LOCALE}/on-demand/movies/{show_key}/details")


# TODO: Validate
def season_url(show_key: str, season_number: int) -> str:
    return build_url(f"{LOCALE}/on-demand/series/{show_key}/season/{season_number}")


# TODO: Validate
def episode_url(show_key: str, season_number: int, episode_key: str) -> str:
    return build_url(
        f"{LOCALE}/on-demand/series/{show_key}/season/{season_number}"
        f"/episode/{episode_key}",
    )


# TODO: Validate
def search_url(query: str) -> str:
    return build_url(f"{LOCALE}/search?query={quote(query)}")


# TODO: Validate
def build_season_key(show_key: str, season_number: int) -> str:
    """Encode the show key into the season key.

    Every entity's data comes from the single file keyed by the show, but the
    base plugin resolves episode files from a season key alone, so the show
    key is carried inside it.
    """
    return f"{show_key}:{season_number}"


# TODO: Validate
def movie_season_key(show_key: str) -> str:
    # A movie has no seasons of its own so its single season is given a
    # fixed number.
    return build_season_key(show_key, 0)


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    show_key, _, season_number = season_key.partition(":")
    return show_key, int(season_number)


# TODO: Validate
def season_episodes(series: SeasonsModel, season_number: int) -> list[Episode]:
    for season in series.seasons:
        if season.number == season_number:
            return season.episodes
    return []


# TODO: Validate
def seasons(series: SeasonsModel) -> list[Season]:
    return series.seasons
