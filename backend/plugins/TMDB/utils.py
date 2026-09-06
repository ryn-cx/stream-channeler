from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import NamedTuple

from tminidb.movie.watch_providers.models import Ad as MovieAd
from tminidb.movie.watch_providers.models import BuyItem as MovieBuyItem
from tminidb.movie.watch_providers.models import FlatrateItem as MovieFlatrateItem
from tminidb.movie.watch_providers.models import FreeItem as MovieFreeItem
from tminidb.movie.watch_providers.models import MovieWatchProvidersModel
from tminidb.movie.watch_providers.models import RentItem as MovieRentItem
from tminidb.movie.watch_providers.models import Us as MovieUs
from tminidb.tv_episode_group.details.models import Episode as TvEpisodeGroupEpisode
from tminidb.tv_episode_group.details.models import Group as TvEpisodeGroup
from tminidb.tv_season.details.models import Episode as TvSeasonEpisode
from tminidb.tv_season.details.models import TvSeasonDetailsModel
from tminidb.tv_season.watch_providers.models import Ad1 as TvSeasonAd
from tminidb.tv_season.watch_providers.models import BuyItem as TvSeasonBuyItem
from tminidb.tv_season.watch_providers.models import (
    FlatrateItem as TvSeasonFlatrateItem,
)
from tminidb.tv_season.watch_providers.models import FreeItem as TvSeasonFreeItem
from tminidb.tv_season.watch_providers.models import TvSeasonWatchProvidersModel
from tminidb.tv_series.watch_providers.models import Ad1 as TvAd
from tminidb.tv_series.watch_providers.models import BuyItem as TvBuyItem
from tminidb.tv_series.watch_providers.models import FlatrateItem as TvFlatrateItem
from tminidb.tv_series.watch_providers.models import FreeItem as TvFreeItem
from tminidb.tv_series.watch_providers.models import TvSeriesWatchProvidersModel

from app.canonical_media.tmdb import (
    tmdb_season_key,
)
from app.media.media_type import TMDBMediaType
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import sorted_plugins

type WatchProviders = (
    MovieWatchProvidersModel | TvSeriesWatchProvidersModel | TvSeasonWatchProvidersModel
)


type Provider = (
    MovieAd
    | MovieFlatrateItem
    | MovieFreeItem
    | MovieRentItem
    | MovieBuyItem
    | TvAd
    | TvFlatrateItem
    | TvFreeItem
    | TvBuyItem
    | TvSeasonAd
    | TvSeasonFlatrateItem
    | TvSeasonFreeItem
    | TvSeasonBuyItem
)


def streaming_providers(
    watch_providers: WatchProviders,
) -> list[Provider]:
    if not (us_results := watch_providers.results.us):
        return []

    providers: list[Provider] = [
        *(us_results.flatrate or []),
        *(us_results.ads or []),
        *(us_results.free or []),
        *(us_results.buy or []),
    ]
    # Only movies have the rent option.
    if isinstance(us_results, MovieUs):
        providers += us_results.rent or []

    # Dedupe the list while maintaining order because some webistes allow you to both
    # rent and buy movies.
    providers_by_id: dict[int, Provider] = {}
    for provider in providers:
        providers_by_id.setdefault(provider.provider_id, provider)
    return list(providers_by_id.values())


def get_media_plugin(provider_name: str) -> type[AbstractPlugin] | None:
    for plugin_class in sorted_plugins():
        if plugin_class.matches_tmdb_provider(provider_name):
            return plugin_class
    return None


def tiel_url(media_type: str, tmdb_media_id: int) -> str:
    """Return the TMDB URL for the title."""
    return f"https://www.themoviedb.org/{media_type}/{tmdb_media_id}"


def parse_release_year(value: str | date) -> int | None:
    """Return the year of the release date or None if it is not known.

    The TMDB API returns an empty string if the date is not known. Converting it to None
    makes it easier to work with."""
    if isinstance(value, date):
        return value.year
    return None


def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


def image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


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
