# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING, NamedTuple

from tminidb.movie.watch_providers.models import BuyItem as MovieBuyItem
from tminidb.movie.watch_providers.models import FlatrateItem as MovieFlatrateItem
from tminidb.movie.watch_providers.models import MovieWatchProvidersModel
from tminidb.movie.watch_providers.models import RentItem as MovieRentItem
from tminidb.tv_episode_group.details.models import Episode as TvEpisodeGroupEpisode
from tminidb.tv_episode_group.details.models import Group as TvEpisodeGroup
from tminidb.tv_season.details.models import Episode as TvSeasonEpisode
from tminidb.tv_season.details.models import TvSeasonDetailsModel
from tminidb.tv_season.watch_providers.models import BuyItem as TvSeasonBuyItem
from tminidb.tv_season.watch_providers.models import (
    FlatrateItem as TvSeasonFlatrateItem,
)
from tminidb.tv_season.watch_providers.models import FreeItem as TvSeasonFreeItem
from tminidb.tv_season.watch_providers.models import RentItem as TvSeasonRentItem
from tminidb.tv_season.watch_providers.models import TvSeasonWatchProvidersModel
from tminidb.tv_series.watch_providers.models import BuyItem as TvBuyItem
from tminidb.tv_series.watch_providers.models import FlatrateItem as TvFlatrateItem
from tminidb.tv_series.watch_providers.models import FreeItem as TvFreeItem
from tminidb.tv_series.watch_providers.models import RentItem as TvRentItem
from tminidb.tv_series.watch_providers.models import TvSeriesWatchProvidersModel

from app.canonical_media.tmdb import (
    tmdb_season_key,
)
from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    PluginWatchProviderItem,
)
from plugins.utils.manage_plugins import sorted_plugins

if TYPE_CHECKING:
    from plugins.TMDB.files import ProvidersFile


type WatchProviders = (
    MovieWatchProvidersModel | TvSeriesWatchProvidersModel | TvSeasonWatchProvidersModel
)


type Provider = (
    MovieFlatrateItem
    | MovieRentItem
    | MovieBuyItem
    | TvFlatrateItem
    | TvFreeItem
    | TvBuyItem
    | TvRentItem
    | TvSeasonFlatrateItem
    | TvSeasonFreeItem
    | TvSeasonBuyItem
    | TvSeasonRentItem
)


# TODO: Validate
def title_url_regex(media_type: TMDBMediaType) -> str:
    return rf"\/{media_type}\/(?P<{media_type}_tmdb_id>\d+)"


# TODO: Validate
def parse_media_identifier(identifier: str) -> tuple[TMDBMediaType, int]:
    """Return the half of the catalogue and the id an identifier names."""
    media_type, _, tmdb_media_id = identifier.partition(" ")
    return TMDBMediaType(media_type), int(tmdb_media_id)


# TODO: Validate
def streaming_providers(
    watch_providers: WatchProviders,
) -> list[Provider]:
    if not (united_states := watch_providers.results.us):
        return []

    providers_by_id: dict[int, Provider] = {}
    for category in ("flatrate", "free", "ads"):
        providers: Sequence[Provider] = getattr(united_states, category, None) or []
        for provider in providers:
            providers_by_id.setdefault(provider.provider_id, provider)
    for category in ("buy", "rent"):
        sold: Sequence[Provider] = getattr(united_states, category, None) or []
        for provider in sold:
            if get_media_plugin(provider.provider_name) is None:
                continue
            providers_by_id.setdefault(provider.provider_id, provider)
    return list(providers_by_id.values())


# TODO: Validate
def get_media_plugin(provider_name: str) -> type[AbstractPlugin] | None:
    for plugin_class in sorted_plugins():
        if plugin_class.matches_tmdb_provider(provider_name):
            return plugin_class
    return None


# TODO: Validate
def watch_provider_items(
    watch_providers: WatchProviders,
    title: str | None,
) -> list[PluginWatchProviderItem]:
    items: list[PluginWatchProviderItem] = []
    for provider in streaming_providers(watch_providers):
        plugin_class = get_media_plugin(provider.provider_name)
        search_url = (
            plugin_class.manual_search_url(title)
            if plugin_class is not None and title
            else None
        )
        items.append(
            PluginWatchProviderItem(
                name=provider.provider_name,
                icon_url=_image_url(
                    "https://image.tmdb.org/t/p/original",
                    provider.logo_path,
                ),
                plugin_key=plugin_class.plugin_name() if plugin_class else None,
                search_url=search_url,
            ),
        )
    return items


# TODO: Validate
def decode_cursor(cursor: str | None) -> tuple[int, int]:
    if not cursor:
        return 1, 0
    page, _, offset = cursor.partition(":")
    return int(page), int(offset or 0)


# TODO: Validate
def encode_cursor(page: int, offset: int) -> str:
    return f"{page}:{offset}"


# TODO: Validate
def provider_names(file: ProvidersFile) -> set[str]:
    return {provider.provider_name for provider in streaming_providers(file.parsed())}


# TODO: Validate
def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


# TODO: Validate
def release_year(value: str | date | None) -> int | None:
    if isinstance(value, date):
        return value.year
    return int(value[:4]) if value else None


# TODO: Validate
def image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def thumbnail_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w500", path)


def runtime_in_seconds(runtime: int | None) -> int | None:
    # If the runtime is not known the API returns None. In all other cases it returns
    # the runtime in minutes.
    return runtime * 60 if runtime else None


def parse_air_datetime(air_date: str | date) -> datetime | None:
    # If the date is not known the API returns an empty string. In all other cases it
    # returns the date as a datetime.
    if isinstance(air_date, str):
        return None
    return tz_datetime.combine(air_date, datetime.min.time())


class SeasonInfo(NamedTuple):
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

    @classmethod
    def from_episode_group(cls, order: int, group: TvEpisodeGroup) -> SeasonInfo:
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

    @classmethod
    def from_season_details(cls, details: TvSeasonDetailsModel) -> SeasonInfo:
        return cls(
            key=tmdb_season_key(TMDBMediaType.tv, details.id),
            name=details.name,
            season_number=details.season_number,
            sort_order=details.season_number,
            poster_path=details.poster_path,
            episodes=details.episodes,
            uses_episode_group=False,
        )
