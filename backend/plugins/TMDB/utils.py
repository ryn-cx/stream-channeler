# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING, NamedTuple

from tminidb.movie.watch_providers.models import BuyItem as MovieBuyItem
from tminidb.movie.watch_providers.models import FlatrateItem as MovieFlatrateItem
from tminidb.movie.watch_providers.models import MovieWatchProvidersModel
from tminidb.movie.watch_providers.models import RentItem as MovieRentItem
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

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    PluginWatchProviderItem,
)
from plugins.utils.manage_plugins import sorted_plugins

if TYPE_CHECKING:
    from plugins.TMDB.files import ProvidersFile, SearchMovie, SearchMulti, SearchTV
    from plugins.TMDB.shared import TMDBShared


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
def media_identifier(media_type: TMDBMediaType, tmdb_id: int) -> str:
    """Return what a search result names a title by, e.g. `tv 1399`."""
    return f"{media_type} {tmdb_id}"


# TODO: Validate
def parse_media_identifier(identifier: str) -> tuple[TMDBMediaType, int]:
    """Return the half of the catalogue and the id an identifier names."""
    media_type, _, tmdb_id = identifier.partition(" ")
    return TMDBMediaType(media_type), int(tmdb_id)


# TODO: Validate
def streaming_providers(
    watch_providers: WatchProviders | None,
) -> list[Provider]:
    if watch_providers is None or not (united_states := watch_providers.results.us):
        return []

    providers_by_id: dict[int, Provider] = {}
    for category in ("flatrate", "free", "ads"):
        providers: Sequence[Provider] = getattr(united_states, category, None) or []
        for provider in providers:
            providers_by_id.setdefault(provider.provider_id, provider)
    for category in ("buy", "rent"):
        sold: Sequence[Provider] = getattr(united_states, category, None) or []
        for provider in sold:
            if get_external_plugin(provider.provider_name) is None:
                continue
            providers_by_id.setdefault(provider.provider_id, provider)
    return list(providers_by_id.values())


# TODO: Validate
def get_external_plugin(provider_name: str) -> type[AbstractPlugin] | None:
    # Asked of the class itself rather than of a base it inherits, because the
    # plugins sit across two base versions and a name is answered by either.
    for plugin_class in sorted_plugins():
        matches = getattr(plugin_class, "matches_tmdb_provider", None)
        if matches is not None and matches(provider_name):
            return plugin_class
    return None


# TODO: Validate
def watch_provider_items(
    watch_providers: WatchProviders | None,
    title: str | None,
) -> list[PluginWatchProviderItem]:
    items: list[PluginWatchProviderItem] = []
    for provider in streaming_providers(watch_providers):
        plugin_class = get_external_plugin(provider.provider_name)
        search_url = (
            plugin_class.manual_search_url(title)
            if plugin_class is not None and title
            else None
        )
        items.append(
            PluginWatchProviderItem(
                name=provider.provider_name,
                icon_url=logo_image_url(provider.logo_path),
                plugin_key=plugin_class.plugin_name() if plugin_class else None,
                search_url=search_url,
            ),
        )
    return items


# TODO: Validate
def found_something(search_file: SearchMovie | SearchTV | SearchMulti) -> bool:
    """Report whether a search came back with anything at all.

    A search TMDB has no answer for is stored empty, and an empty file has no
    results to read out of it.
    """
    parsed = search_file.parsed_or_none()
    return parsed is not None and bool(parsed.results)


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
    return {
        provider.provider_name
        for provider in streaming_providers(file.parsed_or_none())
    }


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
def logo_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


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
def first_search_result(
    plugin: TMDBShared,
    name: str,
    media_type: TMDBMediaType | None,
    year: int | None,
) -> tuple[TMDBMediaType, int] | None:
    """Return which half the first title TMDB returns is from, and its id."""
    if media_type is not None:
        results = plugin.search_media(media_type, name, year).parsed().results
        return (media_type, results[0].id) if results else None

    # A search of both halves also returns people, who are no title and are
    # passed over rather than taken as the first result.
    for result in plugin.search_media(None, name, year).parsed().results:
        # Which half of the catalogue a search of both says a result came
        # from. A multi search also returns people, who are no title and
        # cannot be imported.
        half = {"movie": TMDBMediaType.movie, "tv": TMDBMediaType.tv}.get(
            result.media_type,
        )
        if half is not None:
            return half, result.id
    return None


# TODO: Validate
class EpisodeSource(NamedTuple):
    """One episode of a season, and the number the order gives it."""

    id: int
    number: int
    name: str
    overview: str
    still_path: str | None
    runtime: int | None
    air_date: date | None
    native_season_number: int
    native_episode_number: int


# TODO: Validate
class SeasonSource(NamedTuple):
    """One season of a title, however the title is being read.

    The two ways of reading a series - TMDB's own seasons and a chosen episode
    order - answer with different files holding different shapes, and everything
    that writes a season wants the same handful of things out of either. So both
    are read into this and nothing downstream asks which it was.
    """

    key: str
    name: str | None
    season_number: int
    poster_path: str | None
    episodes: list[EpisodeSource]
