# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from wholoo.search.models import Result

from app.utils import tz_datetime
from plugins.Hulu.helpers import HelperMixin
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)


class SearchMixin(HelperMixin, register=False):
    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.search_file(query)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        results = [
            self._search_result(result)
            for group in search_file.parsed().groups
            for result in group.results
            if result.metrics_info.target_type in ("series", "movie")
        ]
        return PluginSearchResults(results=results)

    def _search_result(self, result: Result) -> PluginSearchResult:
        metrics = result.metrics_info
        content_type = metrics.target_type
        premiere_date = result.entity_metadata.premiere_date
        return PluginSearchResult(
            title=metrics.target_name,
            url=self._show_url(str(metrics.target_id), content_type),
            year=premiere_date.year if premiere_date else None,
            image_url=self._image_url(result.visuals.artwork.horizontal.image.path),
            media_type="Movie" if content_type == "movie" else "Series",
        )
