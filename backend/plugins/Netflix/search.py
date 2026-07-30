# TODO: Validate
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


class SearchMixin(HelperMixin, register=False):
    # Netflix tags each search result with the media type of its title.
    _SEARCH_MEDIA_TYPES: ClassVar[dict[str, str]] = {
        "Show": "TV Show",
        "Movie": "Movie",
    }

    @classmethod
    @override
    def search_url(cls, query: str) -> str:
        return f"https://www.netflix.com/search?q={quote_plus(query)}"

    @override
    def search(self, query: str) -> PluginSearchResults:
        """Search Netflix's movies and TV shows.

        Netflix returns movies and shows intermixed. Suggestion entities
        (collections, autocomplete) carry no title and are skipped.
        """
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)

        results: list[PluginSearchResult] = []
        for section in search_file.parsed().data.page.sections.edges:
            for entity in section.node.entities.edges:
                unified_entity = entity.node.unified_entity
                if unified_entity is None:
                    continue
                media_type = self._SEARCH_MEDIA_TYPES.get(
                    unified_entity.field__typename,
                )
                if media_type is None:
                    continue
                title = entity.node.display_string
                artwork = entity.node.contextual_artwork
                results.append(
                    PluginSearchResult(
                        title=title,
                        url=self._show_url(str(unified_entity.video_id)),
                        image_url=artwork.artwork.url if artwork else None,
                        media_type=media_type,
                    ),
                )
        return PluginSearchResults(results=results)
