# TODO: Validate
"""What every other part of the plugin reads a Paramount+ title by."""

from __future__ import annotations


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://paramountplus.com/{path.lstrip('/')}"


# TODO: Validate
def show_url(show_key: str) -> str:
    return build_url(f"shows/{show_key}/")


# TODO: Validate
def movie_url(movie_key: str) -> str:
    return build_url(f"movies/video/{movie_key}/")


# TODO: Validate
def search_url() -> str:
    return build_url("search/")


# TODO: Validate
def build_season_key(show_key: str, season_number: int) -> str:
    return f"{show_key}:{season_number}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    show_key, _, season_number = season_key.rpartition(":")
    return show_key, int(season_number)
