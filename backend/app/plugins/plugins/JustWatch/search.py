# TODO: Validate
from datetime import timedelta
from typing import override

from app.plugins.plugins.JustWatch.upsert import UpsertMixin
from app.plugins.plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
    PluginSearchResultSource,
)
from app.utils import tz_datetime


class SearchMixin(UpsertMixin, register=False):
    supports_search = True

    # TODO: Consider caching this if it is slow.
    def _get_source_lookup(self) -> dict[str, dict[str, str]]:
        """Build a short_name -> {clear_name, icon_url} mapping from ProvidersLocale."""
        providers_file = self._providers_locale_file()
        providers_file.download_if_outdated()
        return {
            provider["short_name"]: {
                "clear_name": provider["clear_name"],
                "icon_url": self._format_image_url(  # type: ignore[dict-item]
                    provider["icon_url"],
                    profile=100,
                ),
            }
            for provider in providers_file.parsed()
        }

    @override
    def search(self, query: str) -> PluginSearchResults:
        """Search JustWatch for shows/movies.

        The file is cached and only re-downloaded if older than 30 days.
        """
        search_file = self._search_titles_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=30)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()

        source_lookup = self._get_source_lookup()

        results: list[PluginSearchResult] = []
        for edge in parsed.data.search_titles.edges:
            node = edge.node
            poster_url = node.content.poster_url
            image_url = (
                f"{self._images_base_url}{poster_url.replace('{profile}', 's166').replace('{format}', 'webp')}"
                if poster_url
                else None
            )

            seen_sources: dict[str, PluginSearchResultSource] = {}
            for offer in node.offers:
                short_name = offer.package.short_name
                if short_name not in seen_sources:
                    info = source_lookup.get(short_name)
                    seen_sources[short_name] = PluginSearchResultSource(
                        name=info["clear_name"] if info else short_name,
                        icon_url=info["icon_url"] if info else None,
                    )

            media_type = "TV Show" if node.object_type == "SHOW" else "Movie"
            results.append(
                PluginSearchResult(
                    title=node.content.title,
                    url=f"justwatch.com{node.content.full_path}",
                    year=node.content.original_release_year,
                    image_url=image_url,
                    media_type=media_type,
                    sources=list(seen_sources.values()),
                ),
            )

        return PluginSearchResults(
            has_source_selection=True,
            results=results,
        )
