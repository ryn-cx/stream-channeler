# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, override

from app.media.media_type import MediaType
from plugins.TMDB.files import (
    MovieDetails,
    backdrop_image_url,
    logo_image_url,
    poster_image_url,
    release_year,
)
from plugins.TMDB.lookup import LookupMixin
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    PluginMediaInfo,
    PluginWatchProviderItem,
)
from plugins.utils.manage_plugins import sorted_plugins

STREAMING_CATEGORIES = ("flatrate", "free", "ads")

_MEDIA_TYPE_LABELS = {MediaType.movie: "Movie", MediaType.tv: "TV Show"}


# TODO: Validate
def media_identifier(media_type: MediaType, tmdb_id: int) -> str:
    """Return what a search result names a title by, e.g. `tv 1399`."""
    return f"{media_type} {tmdb_id}"


# TODO: Validate
def parse_media_identifier(identifier: str) -> tuple[MediaType, int]:
    """Return the half of the catalogue and the id an identifier names."""
    media_type, _, tmdb_id = identifier.partition(" ")
    return MediaType(media_type), int(tmdb_id)


# TODO: Validate
class MediaInfoMixin(LookupMixin, register=False):
    # TODO: Validate
    @override
    def media_info(self, media_identifier: str) -> PluginMediaInfo | None:
        media_type, tmdb_id = parse_media_identifier(media_identifier)
        detail_file = self.auto_updating_media_detail(media_type, tmdb_id)
        providers = self.auto_updating_watch_providers(media_type, tmdb_id).parsed()
        # Which of the two shapes the detail is has to be read off the file rather
        # than the parsed model, because a model whose module was reloaded after a
        # schema change is no longer an instance of the class imported here.
        detail: dict[str, Any]
        # A title with no poster of its own can still be shown by a poster one of
        # its seasons carries.
        season_poster_path: str | None
        if isinstance(detail_file, MovieDetails):
            detail = detail_file.parsed()
            title = detail["title"]
            year = release_year(detail["release_date"])
            end_year = None
            number_of_seasons = None
            number_of_episodes = None
            runtime = detail["runtime"]
            season_poster_path = None
        else:
            detail = detail_file.parsed()
            title = detail["name"]
            year = release_year(detail["first_air_date"])
            end_year = release_year(detail["last_air_date"])
            number_of_seasons = detail["number_of_seasons"]
            number_of_episodes = detail["number_of_episodes"]
            runtime = None
            season_poster_path = next(
                (
                    season["poster_path"]
                    for season in detail["seasons"]
                    if season["poster_path"]
                ),
                None,
            )

        # Either image stands in for the other when its own path is missing, sized
        # for the slot it fills rather than the slot it came from.
        poster_path = detail["poster_path"] or season_poster_path
        backdrop_path = detail["backdrop_path"]
        return PluginMediaInfo(
            title=title,
            media_type=_MEDIA_TYPE_LABELS[media_type],
            tagline=detail["tagline"] or None,
            overview=detail["overview"] or None,
            poster_url=poster_image_url(poster_path or backdrop_path),
            backdrop_url=backdrop_image_url(backdrop_path or poster_path),
            year=year,
            end_year=end_year,
            status=detail["status"],
            rating=detail["vote_average"],
            vote_count=detail["vote_count"],
            number_of_seasons=number_of_seasons,
            number_of_episodes=number_of_episodes,
            runtime=runtime,
            genres=[genre["name"] for genre in detail["genres"]],
            providers=_watch_provider_items(providers, title),
        )


# TODO: Validate
def streaming_providers(
    watch_providers: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if watch_providers is None or not (
        united_states := watch_providers["results"].get("US")
    ):
        return []

    providers_by_id: dict[int, dict[str, Any]] = {}
    for category in STREAMING_CATEGORIES:
        providers: Sequence[dict[str, Any]] = united_states.get(category, ())
        for provider in providers:
            providers_by_id.setdefault(provider["provider_id"], provider)
    return list(providers_by_id.values())


# TODO: Validate
def plugin_for_tmdb_name(provider_name: str) -> type[AbstractPlugin] | None:
    plugin_classes = sorted_plugins()
    for plugin_class in plugin_classes:
        if provider_name in plugin_class.TMDB_PROVIDER_NAMES:
            return plugin_class
    for plugin_class in plugin_classes:
        if plugin_class.matches_tmdb_provider(provider_name):
            return plugin_class
    return None


# TODO: Validate
def _watch_provider_items(
    watch_providers: dict[str, Any] | None,
    title: str | None,
) -> list[PluginWatchProviderItem]:
    items: list[PluginWatchProviderItem] = []
    for provider in streaming_providers(watch_providers):
        plugin_class = plugin_for_tmdb_name(provider["provider_name"])
        search_url = (
            plugin_class.search_url(title)
            if plugin_class is not None and title
            else None
        )
        items.append(
            PluginWatchProviderItem(
                name=provider["provider_name"],
                icon_url=logo_image_url(provider["logo_path"]),
                plugin_key=plugin_class.plugin_key() if plugin_class else None,
                search_url=search_url,
            ),
        )
    return items
