# TODO: Validate
"""Searching Netflix's own catalogue."""

from __future__ import annotations

from datetime import timedelta
from typing import ClassVar, override
from urllib.parse import quote_plus

from app.utils import tz_datetime
from plugins.Netflix.helpers import HelperMixin
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)

_SEARCH_MAX_AGE = timedelta(days=30)


# TODO: Validate
class SearchMixin(HelperMixin, register=False):
    """Searching Netflix."""

    # Netflix tags each search result with the media type of its title.
    _SEARCH_MEDIA_TYPES: ClassVar = {
        "Show": "TV Show",
        "Movie": "Movie",
    }

    # TODO: Validate
    @classmethod
    @override
    def search_url(cls, query: str) -> str:
        return cls.build_url(f"search?q={quote_plus(query)}")

    # TODO: Validate
    @override
    def search(self, query: str, cursor: str | None = None) -> PluginSearchResults:
        """Search Netflix's movies and TV shows.

        Netflix returns movies and shows intermixed. Suggestion entities
        (collections, autocomplete) carry no title and are skipped.
        """
        search_file = self.search_file(query, cursor)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)

        next_cursor: str | None = None
        results: list[PluginSearchResult] = []
        for section in search_file.parsed()["data"]["page"]["sections"]["edges"]:
            section_results = 0
            for entity in section["node"]["entities"]["edges"]:
                unified_entity = entity["node"].get("unifiedEntity")
                if unified_entity is None:
                    continue
                media_type = self._SEARCH_MEDIA_TYPES.get(
                    unified_entity["__typename"],
                )
                if media_type is None:
                    continue
                title = entity["node"]["displayString"]
                artwork = entity["node"].get("contextualArtwork")
                media_identifier = str(unified_entity["videoId"])
                results.append(
                    PluginSearchResult(
                        title=title,
                        url=self._show_url(media_identifier),
                        image_url=artwork["artwork"]["url"] if artwork else None,
                        media_type=media_type,
                        media_identifier=media_identifier,
                    ),
                )
                section_results += 1
            # Only the section holding the titles is worth paging through; the
            # suggestion section alongside it never produces a result.
            page_info = section["node"]["entities"].get("pageInfo")
            if section_results and page_info and page_info["hasNextPage"]:
                next_cursor = page_info["endCursor"]
        return PluginSearchResults(results=results, next_cursor=next_cursor)
