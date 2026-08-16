# TODO: Validate
"""Searching Prime Video's own catalogue."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.Amazon.helpers import HelperMixin
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
    paginate_search_results,
)


# TODO: Validate
class SearchMixin(HelperMixin, register=False):
    """Searching Prime Video."""

    # Prime Video answers a search with every match at once, so pages are cut out
    # of that one download rather than requested one at a time.
    # TODO: Validate
    @override
    def search(self, query: str, cursor: str | None = None) -> PluginSearchResults:
        search_file = self.search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=7)
        search_file.download_if_outdated(minimum_timestamp)
        results = [
            PluginSearchResult(
                title=result.title,
                url=self._detail_url(result.key),
                year=result.year,
                image_url=result.image_url,
                media_type=result.entity_type,
                media_identifier=result.key,
            )
            for result in search_file.results()
        ]
        return paginate_search_results(results, cursor, self.SEARCH_PAGE_SIZE)
