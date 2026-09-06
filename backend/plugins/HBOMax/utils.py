# TODO: Validate
"""What every other part of the plugin reads an HBO Max title by."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from minbo.movie.models import Idref14 as MovieContent
    from minbo.movie.models import MovieModel
    from minbo.show.models import Episode, Season, ShowModel
    from minbo.show.models import Idref14 as TitleContent


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://play.hbomax.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"show/{title_key}")


# TODO: Validate
def movie_url(movie_key: str) -> str:
    return build_url(f"movie/{movie_key}")


# TODO: Validate
def search_url(query: str) -> str:
    return build_url(f"search/result?q={quote(query)}")


# TODO: Validate
def build_season_key(title_key: str, season_number: int) -> str:
    return f"{title_key}:{season_number}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    title_key, _, season_number = season_key.rpartition(":")
    return title_key, int(season_number)


# TODO: Validate
def build_episode_key(season_key: str, episode_number: int) -> str:
    return f"{season_key}:{episode_number}"


# TODO: Validate
def title_content(title: ShowModel) -> TitleContent:
    return title.props.page_props.mapped_data.idref14


# TODO: Validate
def movie_content(movie: MovieModel) -> MovieContent:
    return movie.props.page_props.mapped_data.idref14


# TODO: Validate
def season_numbers(title: ShowModel) -> list[int]:
    return [season.season_number for season in title_content(title).seasons]


# TODO: Validate
def season_entry(title: ShowModel, season_number: int) -> Season:
    for season in title_content(title).seasons:
        if season.season_number == season_number:
            return season
    msg = f"Season {season_number} not found."
    raise ValueError(msg)


# TODO: Validate
def season_episodes(season: ShowModel, season_number: int) -> list[Episode]:
    for entry in title_content(season).seasons:
        if entry.season_number == season_number:
            return entry.episodes
    msg = f"Season {season_number} not found."
    raise ValueError(msg)
