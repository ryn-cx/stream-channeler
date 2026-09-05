# TODO: Validate
"""What every other part of the plugin reads an HBO Max title by."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from minbo.movie.models import Idref14 as MovieContent
    from minbo.movie.models import MovieModel
    from minbo.show.models import Episode, Season, ShowModel
    from minbo.show.models import Idref14 as ShowContent


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://play.hbomax.com/{path.lstrip('/')}"


# TODO: Validate
def show_url(show_key: str) -> str:
    return build_url(f"show/{show_key}")


# TODO: Validate
def movie_url(movie_key: str) -> str:
    return build_url(f"movie/{movie_key}")


# TODO: Validate
def search_url(query: str) -> str:
    return build_url(f"search/result?q={quote(query)}")


# TODO: Validate
def build_season_key(show_key: str, season_number: int) -> str:
    return f"{show_key}:{season_number}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    show_key, _, season_number = season_key.rpartition(":")
    return show_key, int(season_number)


# TODO: Validate
def build_episode_key(season_key: str, episode_number: int) -> str:
    return f"{season_key}:{episode_number}"


# TODO: Validate
def show_content(show: ShowModel) -> ShowContent:
    return show.props.page_props.mapped_data.idref14


# TODO: Validate
def movie_content(movie: MovieModel) -> MovieContent:
    return movie.props.page_props.mapped_data.idref14


# TODO: Validate
def season_numbers(show: ShowModel) -> list[int]:
    return [season.season_number for season in show_content(show).seasons]


# TODO: Validate
def season_entry(show: ShowModel, season_number: int) -> Season:
    for season in show_content(show).seasons:
        if season.season_number == season_number:
            return season
    msg = f"Season {season_number} not found."
    raise ValueError(msg)


# TODO: Validate
def season_episodes(season: ShowModel, season_number: int) -> list[Episode]:
    for entry in show_content(season).seasons:
        if entry.season_number == season_number:
            return entry.episodes
    msg = f"Season {season_number} not found."
    raise ValueError(msg)
