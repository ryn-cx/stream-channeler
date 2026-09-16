# TODO: Validate
"""What every other part of the plugin reads an HBO Max title by."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from minbo.movie.models import Idref14 as MovieContent
    from minbo.movie.models import Item as MovieCarouselItem
    from minbo.movie.models import Item1 as MovieSeoCarouselItem
    from minbo.movie.models import MovieModel
    from minbo.show.models import Episode, Season, ShowModel
    from minbo.show.models import Idref14 as TitleContent
    from minbo.show.models import Item1 as TitleCarouselItem
    from minbo.show.models import Item2 as TitleSeoCarouselItem


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


# TODO: Validate
def title_related_urls(title: ShowModel) -> list[str]:
    mapped_data = title.props.page_props.mapped_data
    return _carousel_urls([*mapped_data.idref64.items, *mapped_data.idref79.items])


# TODO: Validate
def movie_related_urls(movie: MovieModel) -> list[str]:
    mapped_data = movie.props.page_props.mapped_data
    return _carousel_urls([*mapped_data.idref57.items, *mapped_data.idref71.items])


# TODO: Validate
def _carousel_urls(
    items: Sequence[
        TitleCarouselItem
        | TitleSeoCarouselItem
        | MovieCarouselItem
        | MovieSeoCarouselItem
    ],
) -> list[str]:
    urls: dict[str, None] = {}
    for item in items:
        if item.series_id:
            urls[title_url(str(item.series_id))] = None
        elif item.feature_id:
            urls[movie_url(str(item.feature_id))] = None
    return list(urls)
