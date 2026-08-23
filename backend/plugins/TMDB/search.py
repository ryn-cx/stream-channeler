# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import Any, ClassVar, override

from app.media.media_type import MediaType
from app.utils import tz_datetime
from plugins.TMDB.files import (
    backdrop_image_url,
    poster_image_url,
    release_year,
    title_page_url,
)
from plugins.TMDB.lookup import LookupMixin
from plugins.TMDB.media_info import media_identifier
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)

_SEARCH_MAX_AGE = timedelta(days=7)


# TODO: Validate
class SearchMixin(LookupMixin, register=False):
    # A multi search also returns people, who cannot be added to a channel.
    _SEARCH_MEDIA_TYPES: ClassVar = {
        "movie": "Movie",
        "tv": "TV Show",
    }

    # TODO: Validate
    @override
    def search(self, query: str, cursor: str | None = None) -> PluginSearchResults:
        """Search every title TMDB knows about, whatever it streams on.

        A result's URL is the title's own TMDB page rather than a stream, since
        `import_url` reads that page to find where the title can be watched.
        """
        page = int(cursor) if cursor else 1
        search_file = self.multi_search_file(query, page)
        search_file.download_if_outdated(tz_datetime.now() - _SEARCH_MAX_AGE)
        parsed = search_file.parsed()

        results = [
            self._search_result(result)
            for result in parsed["results"]
            if result["media_type"] in self._SEARCH_MEDIA_TYPES
        ]
        return PluginSearchResults(
            results=results,
            next_cursor=str(page + 1) if page < parsed["total_pages"] else None,
        )

    # TODO: Validate
    def _search_result(self, result: dict[str, Any]) -> PluginSearchResult:
        # A movie carries its title and release date, a show its name and first
        # air date, and a multi search returns the two mixed together.
        title: str | None
        if result["media_type"] == "movie":
            title = result.get("title") or result.get("original_title")
            year = release_year(result.get("release_date"))
        else:
            title = result.get("name") or result.get("original_name")
            year = release_year(result.get("first_air_date"))

        if title is None:
            msg = f"TMDB {result['media_type']} {result['id']} has no title"
            raise ValueError(msg)

        return PluginSearchResult(
            title=title,
            url=title_page_url(result["media_type"], result["id"]),
            year=year,
            image_url=poster_image_url(result["poster_path"])
            or backdrop_image_url(result["backdrop_path"]),
            media_type=self._SEARCH_MEDIA_TYPES[result["media_type"]],
            media_identifier=media_identifier(
                MediaType(result["media_type"]),
                result["id"],
            ),
        )
