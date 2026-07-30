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


class SearchMixin(FileMixin, register=False):
    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.shows_search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=7)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()
        results = [
            PluginSearchResult(
                title=hit.field_source.title,
                url=self.build_url(hit.field_source.url),
                image_url=self.build_url(hit.field_source.thumbnail),
                media_type="TV Show",
            )
            for hit in parsed.hits.hits
        ]
        return PluginSearchResults(results=results)
