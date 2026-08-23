# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.NHKWorld.files import FileMixin
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)


# TODO: Validate
class SearchMixin(FileMixin, register=False):
    # TODO: Validate
    @override
    def search(self, query: str, cursor: str | None = None) -> PluginSearchResults:
        offset = int(cursor) if cursor else 0
        search_file = self.shows_search_file(query, offset)
        minimum_timestamp = tz_datetime.now() - timedelta(days=7)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()
        results = [
            PluginSearchResult(
                title=hit["_source"]["title"],
                url=self.build_url(hit["_source"]["url"]),
                image_url=self.build_url(hit["_source"]["thumbnail"]),
                media_type="TV Show",
                media_identifier=hit["_source"]["slug"],
            )
            for hit in parsed["hits"]["hits"]
        ]
        next_offset = offset + len(results)
        return PluginSearchResults(
            results=results,
            next_cursor=(
                str(next_offset)
                if results and next_offset < parsed["hits"]["total"]["value"]
                else None
            ),
        )
