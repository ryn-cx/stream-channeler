# TODO: Validate
"""Searching Hulu's own catalogue."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from wholoo.search.models import Result

from app.utils import tz_datetime
from plugins.Hulu.files import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.Hulu.helpers import HelperMixin
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
    paginate_search_results,
)


# TODO: Validate
class SearchMixin(HelperMixin, register=False):
    """Searching Hulu."""

    # Hulu answers a search with every match at once, so pages are cut out of
    # that one download rather than requested one at a time.
    # TODO: Validate
    @override
    def search(self, query: str, cursor: str | None = None) -> PluginSearchResults:
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        results = [
            self._search_result(result)
            for group in search_file.parsed().groups
            for result in group.results
            if result.metrics_info.target_type in (SERIES_MEDIA_TYPE, MOVIE_MEDIA_TYPE)
        ]
        return paginate_search_results(results, cursor, self.SEARCH_PAGE_SIZE)

    # TODO: Validate
    def _search_result(self, result: Result) -> PluginSearchResult:
        metrics = result.metrics_info
        media_type = metrics.target_type
        title_key = str(metrics.target_id)
        premiere_date = result.entity_metadata.premiere_date
        return PluginSearchResult(
            title=metrics.target_name,
            url=self._show_url(title_key, media_type),
            year=premiere_date.year if premiere_date else None,
            image_url=self._image_url(result.visuals.artwork.horizontal.image.path),
            media_type="Movie" if media_type == MOVIE_MEDIA_TYPE else "Series",
            media_identifier=self.media_identifier(media_type, title_key),
        )
