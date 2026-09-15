# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any, NamedTuple

from tminidb.tv_episode_group.details.models import Episode as TvEpisodeGroupEpisode
from tminidb.tv_episode_group.details.models import Group as TvEpisodeGroup
from tminidb.tv_season.details.models import Episode as TvSeasonEpisode
from tminidb.tv_season.details.models import TvSeasonDetailsModel

from app.media.media_type import TMDBMediaType
from app.tmdb_media.tmdb import (
    tmdb_season_key,
)


# TODO: Validate
def tmdb_url(media_type: str, tmdb_media_id: int) -> str:
    """Return the TMDB URL for the title."""
    return f"https://www.themoviedb.org/{media_type}/{tmdb_media_id}"


# TODO: Validate
def parse_release_year(value: str | date) -> int | None:
    """Return the year of the release date or None if it is not known.

    The TMDB API returns an empty string if the date is not known. Converting it to None
    makes it easier to work with."""
    if isinstance(value, date):
        return value.year
    return None


# TODO: Validate
def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


# TODO: Validate
def image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def thumbnail_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w500", path)


# TODO: Validate
class TMDBSeasonInfo(NamedTuple):
    """Season information from the season details or episode group.

    Normally the data structure of the season details and episode groups are different,
    this class creates a unified representation for both episode groups and season
    details."""

    key: str
    name: str | None
    season_number: int | None
    sort_order: int
    poster_path: str | None
    episodes: Sequence[TvSeasonEpisode | TvEpisodeGroupEpisode]
    uses_episode_group: bool

    # TODO: Validate
    @classmethod
    def from_episode_group(cls, order: int, group: TvEpisodeGroup) -> TMDBSeasonInfo:
        return cls(
            key=tmdb_season_key(TMDBMediaType.tv, order),
            name=group.name,
            # Technically there are no season numbers, but it makes sorting easier if a
            # fake season number is created.
            season_number=order,
            sort_order=order,
            poster_path=None,
            episodes=group.episodes,
            uses_episode_group=True,
        )

    # TODO: Validate
    @classmethod
    def from_season_details(cls, details: TvSeasonDetailsModel) -> TMDBSeasonInfo:
        return cls(
            key=tmdb_season_key(TMDBMediaType.tv, details.id),
            name=details.name,
            season_number=details.season_number,
            sort_order=details.season_number,
            poster_path=details.poster_path,
            episodes=details.episodes,
            uses_episode_group=False,
        )


# TODO: Validate
def watch_provider_names(watch_providers: Any) -> set[str]:  # noqa: ANN401 - One of the strict and optional models of three media types.
    us_results = watch_providers.results.us
    if not us_results:
        return set()
    return {
        provider.provider_name
        for offering in ("flatrate", "ads", "free", "buy", "rent")
        for provider in getattr(us_results, offering, None) or []
    }
