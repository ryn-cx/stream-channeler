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

from app.canonical_media.keys import tmdb_season_key
from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    PluginWatchProviderItem,
)
from plugins.utils.manage_plugins import sorted_plugins
from collections.abc import Sequence

if TYPE_CHECKING:
    from tminidb.movie.details.models import MovieDetailsModel
    from tminidb.tv_series.details.models import TvSeriesDetailsModel

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
    media_type, _, tmdb_media_key = identifier.partition(" ")
    return TMDBMediaType(media_type), int(tmdb_media_key)


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
def poster_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w500", path)


# TODO: Validate
def backdrop_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def still_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def poster_original_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def backdrop_thumbnail_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w300", path)


# TODO: Validate
def still_thumbnail_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w300", path)


# TODO: Validate
def get_first_image(
    details: MovieDetailsModel | TvSeriesDetailsModel,
    *,
    thumbnail: bool,
) -> str | None:
    if details.backdrop_path:
        if thumbnail:
            return backdrop_thumbnail_url(details.backdrop_path)
        return backdrop_image_url(details.backdrop_path)
    if thumbnail:
        return poster_image_url(details.poster_path)
    return poster_original_url(details.poster_path)


# TODO: Validate
def duration_seconds(runtime: int | None) -> int | None:
    return runtime * 60 if runtime else None


# TODO: Validate
def air_datetime(air_date: str | date | None) -> datetime | None:
    # A date TMDB does not have yet comes back as an empty string rather than
    # being left out, and every date the API answers with arrives as the text
    # TMDB wrote rather than as a date.
    if not air_date:
        return None
    if isinstance(air_date, str):
        air_date = date.fromisoformat(air_date)
    return tz_datetime.combine(air_date, datetime.min.time())


# TODO: Validate
class SeasonInfo(NamedTuple):
    """Holds Season information from the season details or episode group.

    Normally the data structure of the season details and episode group are different,
    this class consolidates them into a single interface."""

    key: str
    name: str | None
    season_number: int | None
    sort_order: int
    poster_path: str | None
    episodes: Sequence[TvSeasonEpisode | TvEpisodeGroupEpisode]
    uses_episode_group: bool

    # TODO: Validate
    @classmethod
    def from_episode_group(cls, order: int, group: TvEpisodeGroup) -> SeasonInfo:
        return cls(
            key=tmdb_season_key(TMDBMediaType.tv, order),
            name=group.name,
            # Technically incorrect because there is no real season number, but it makes
            # sorting easier so it's allowed.
            season_number=order,
            sort_order=order,
            poster_path=None,
            episodes=group.episodes,
            uses_episode_group=True,
        )

    # TODO: Validate
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
