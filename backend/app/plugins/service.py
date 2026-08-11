# TODO: Validate
"""Plugin service functions."""

from typing import Protocol

from sqlmodel import Session
from tminidb.movie_details.models import MovieDetailsModel
from tminidb.movie_watch_providers.models import MovieWatchProvidersModel
from tminidb.tv_series_details.models import TvSeriesDetailsModel
from tminidb.tv_watch_providers.models import TvWatchProvidersModel

from app.media.media_type import MediaType
from app.plugins.schemas import (
    TMDBMatch,
    TMDBMediaInfo,
    TMDBWatchProviderItem,
)
from plugins.TMDB import TMDB
from plugins.TMDB.files import (
    MovieDetails,
    backdrop_image_url,
    logo_image_url,
    poster_image_url,
    release_year,
)
from plugins.utils.manage_plugins import sorted_plugins

_STREAMING_CATEGORIES = ("flatrate", "free", "ads")


# TODO: Validate
class WatchProvider(Protocol):
    logo_path: str
    provider_id: int
    provider_name: str


# TODO: Validate
def _watch_provider_items(
    watch_providers: TvWatchProvidersModel | MovieWatchProvidersModel | None,
    title: str | None,
) -> list[TMDBWatchProviderItem]:
    if watch_providers is None or not (
        us := getattr(watch_providers.results, "us", None)
    ):
        return []

    provider_plugins = {
        provider_name: plugin_class
        for plugin_class in sorted_plugins()
        for provider_name in plugin_class.TMDB_PROVIDER_NAMES
    }
    providers_by_id: dict[int, WatchProvider] = {}
    for category in _STREAMING_CATEGORIES:
        providers: list[WatchProvider] = getattr(us, category, None) or []
        for provider in providers:
            providers_by_id.setdefault(provider.provider_id, provider)

    items: list[TMDBWatchProviderItem] = []
    for provider in providers_by_id.values():
        plugin_class = provider_plugins.get(provider.provider_name)
        search_url = (
            plugin_class.search_url(title)
            if plugin_class is not None and title
            else None
        )
        items.append(
            TMDBWatchProviderItem(
                name=provider.provider_name,
                icon_url=logo_image_url(provider.logo_path),
                plugin_key=plugin_class.plugin_key() if plugin_class else None,
                search_url=search_url,
            ),
        )
    return items


# TODO: Validate
def tmdb_match(
    session: Session,
    title: str,
    media_type: MediaType,
    year: int | None = None,
) -> TMDBMatch | None:
    """Return the TMDB title that best matches a plugin's search result.

    A plugin search result only carries what its own service knows, so the
    matching TMDB title has to be found by searching for it. Resolved on demand
    rather than for every result, since only the ones opened are needed.
    """
    search_file = TMDB(session).auto_updating_search_media(media_type, title, year)
    results = search_file.parsed().results
    if not results:
        return None
    return TMDBMatch(tmdb_id=results[0].id, media_type=media_type)


# TODO: Validate
def tmdb_media_info(
    session: Session,
    media_type: MediaType,
    tmdb_id: int,
) -> TMDBMediaInfo | None:
    tmdb = TMDB(session)
    detail_file = tmdb.auto_updating_media_detail(media_type, tmdb_id)
    providers = tmdb.auto_updating_watch_providers(media_type, tmdb_id).parsed()
    # Which of the two shapes the detail is has to be read off the file rather
    # than the parsed model, because a model whose module was reloaded after a
    # schema change is no longer an instance of the class imported here.
    detail: MovieDetailsModel | TvSeriesDetailsModel
    if isinstance(detail_file, MovieDetails):
        detail = detail_file.parsed()
        title = detail.title
        year = release_year(detail.release_date)
        end_year = None
        number_of_seasons = None
        number_of_episodes = None
        runtime = detail.runtime
    else:
        detail = detail_file.parsed()
        title = detail.name
        year = release_year(detail.first_air_date)
        end_year = release_year(detail.last_air_date)
        number_of_seasons = detail.number_of_seasons
        number_of_episodes = detail.number_of_episodes
        runtime = None
    return TMDBMediaInfo(
        title=title,
        tagline=detail.tagline or None,
        overview=detail.overview or None,
        poster_url=poster_image_url(detail.poster_path),
        backdrop_url=backdrop_image_url(detail.backdrop_path),
        year=year,
        end_year=end_year,
        status=detail.status,
        rating=detail.vote_average,
        vote_count=detail.vote_count,
        number_of_seasons=number_of_seasons,
        number_of_episodes=number_of_episodes,
        runtime=runtime,
        genres=[genre.name for genre in detail.genres],
        providers=_watch_provider_items(providers, title),
    )
