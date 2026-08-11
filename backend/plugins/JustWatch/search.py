# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import override

from app.utils import tz_datetime
from plugins.JustWatch.helpers import HelperMixin
from plugins.utils.abstract_plugin import PluginSearchResult, PluginSearchResults


# TODO: Validate
class SearchMixin(HelperMixin, register=False):
    # TODO: Validate
    @override
    def search(self, query: str, cursor: str | None = None) -> PluginSearchResults:
        search_file = self.search_titles_file(query, cursor)
        minimum_timestamp = tz_datetime.now() - timedelta(days=30)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()

        results: list[PluginSearchResult] = []
        for edge in parsed.data.search_titles.edges:
            node = edge.node
            image_url = self._format_image_url(
                node.content.poster_url,
                166,
                "webp",
            )
            media_type = "TV Show" if node.object_type == "SHOW" else "Movie"
            results.append(
                PluginSearchResult(
                    title=node.content.title,
                    url=f"{self._domain()}{node.content.full_path}",
                    year=node.content.original_release_year,
                    image_url=image_url,
                    media_type=media_type,
                ),
            )

        page_info = parsed.data.search_titles.page_info
        return PluginSearchResults(
            results=results,
            next_cursor=page_info.end_cursor if page_info.has_next_page else None,
        )
