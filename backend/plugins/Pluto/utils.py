# TODO: Validate
"""What every other part of the plugin reads a Pluto TV title by."""

from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.Pluto.constants import LOCALE

if TYPE_CHECKING:
    from collections.abc import Sequence

    from notaplanet.items.models import Cover as ItemCover
    from notaplanet.seasons.models import Cover as SeasonCover
    from notaplanet.seasons.models import Episode, Season, SeasonsModel


# TODO: Validate
def _cover_ratio(cover: ItemCover | SeasonCover) -> float:
    width, _, height = cover.aspect_ratio.partition(":")
    return float(width) / float(height)


# TODO: Validate
def poster_url(covers: Sequence[ItemCover | SeasonCover]) -> str | None:
    portrait = [cover for cover in covers if _cover_ratio(cover) < 1]
    return min(portrait, key=_cover_ratio).url if portrait else None


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://pluto.tv/{path.lstrip('/')}"


# TODO: Validate
def series_url(title_key: str) -> str:
    return build_url(f"{LOCALE}/on-demand/series/{title_key}/details")


# TODO: Validate
def movie_url(title_key: str) -> str:
    return build_url(f"{LOCALE}/on-demand/movies/{title_key}/details")


# TODO: Validate
def season_url(title_key: str, season_number: int) -> str:
    return build_url(f"{LOCALE}/on-demand/series/{title_key}/season/{season_number}")


# TODO: Validate
def episode_url(title_key: str, season_number: int, episode_key: str) -> str:
    return build_url(
        f"{LOCALE}/on-demand/series/{title_key}/season/{season_number}"
        f"/episode/{episode_key}",
    )


# TODO: Validate
def build_season_key(title_key: str, season_number: int) -> str:
    """Encode the title key into the season key.

    Every entity's data comes from the single file keyed by the title, but the
    base plugin resolves episode files from a season key alone, so the title
    key is carried inside it.
    """
    return f"{title_key}:{season_number}"


# TODO: Validate
def movie_season_key(title_key: str) -> str:
    # A movie has no seasons of its own so its single season is given a
    # fixed number.
    return build_season_key(title_key, 0)


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    title_key, _, season_number = season_key.partition(":")
    return title_key, int(season_number)


# TODO: Validate
def season_episodes(series: SeasonsModel, season_number: int) -> list[Episode]:
    for season in series.seasons:
        if season.number == season_number:
            return season.episodes
    return []


# TODO: Validate
def seasons(series: SeasonsModel) -> list[Season]:
    return series.seasons
