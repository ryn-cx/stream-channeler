# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import ClassVar, override

from tminidb.search.multi.models import Result as MultiResult
from tminidb.search.multi.models import SearchMultiModel

from app.media.media_type import MediaType
from app.utils import tz_datetime
from plugins.TMDB.constants import media_url
from plugins.TMDB.helpers import (
    backdrop_image_url,
    poster_image_url,
    release_year,
)
from plugins.TMDB.lookup import LookupMixin
from plugins.TMDB.media_info import media_identifier
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)


# TODO: Validate
def _decode_cursor(cursor: str | None) -> tuple[int, int]:
    if not cursor:
        return 1, 0
    page, _, offset = cursor.partition(":")
    return int(page), int(offset or 0)


# TODO: Validate
def _encode_cursor(page: int, offset: int) -> str:
    return f"{page}:{offset}"


# TODO: Validate
class SearchMixin(LookupMixin, register=False):
    # A multi search also returns people, who cannot be added to a channel.
    _SEARCH_MEDIA_TYPES: ClassVar = {
        "movie": "Movie",
        "tv": "TV Show",
    }

    # TODO: Validate
    @classmethod
    def search_page_size(cls) -> int:
        return 20

    # TODO: Validate
    @override
    def in_app_search(
        self,
        query: str,
        cursor: str | None = None,
    ) -> PluginSearchResults:
        """Search every title TMDB knows about, whatever it streams on.

        A result's URL is the title's own TMDB page rather than a stream, since
        `import_url` reads that page to find where the title can be watched.
        """
        page, offset = _decode_cursor(cursor)
        results: list[PluginSearchResult] = []
        next_cursor: str | None = None

        while len(results) < self.search_page_size():
            parsed = self._multi_search_page(query, page)
            matches = [
                self._search_result(result)
                for result in parsed.results
                if result.media_type in self._SEARCH_MEDIA_TYPES
            ][offset:]

            wanted = self.search_page_size() - len(results)
            results.extend(matches[:wanted])
            if len(matches) > wanted:
                next_cursor = _encode_cursor(page, offset + wanted)
                break

            page += 1
            offset = 0
            if page > parsed.total_pages:
                next_cursor = None
                break
            next_cursor = _encode_cursor(page, 0)

        return PluginSearchResults(results=results, next_cursor=next_cursor)

    # TODO: Validate
    def _multi_search_page(self, query: str, page: int) -> SearchMultiModel:
        search_file = self.multi_search_file(query, page)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return search_file.parsed()

    # TODO: Validate
    def _search_result(self, result: MultiResult) -> PluginSearchResult:
        # A movie carries its title and release date, a show its name and first
        # air date, and a multi search returns the two mixed together.
        title: str | None
        media_type: MediaType
        if result.media_type == "movie":
            media_type = MediaType.movie
            title = result.title or result.original_title
            year = release_year(result.release_date)
        else:
            media_type = MediaType.tv
            title = result.name or result.original_name
            year = release_year(result.first_air_date)

        if not title:
            msg = f"TMDB {result.media_type} {result.id} has no title"
            raise ValueError(msg)

        return PluginSearchResult(
            title=title,
            url=media_url(media_type, result.id),
            year=year,
            image_url=poster_image_url(result.poster_path)
            or backdrop_image_url(result.backdrop_path),
            media_type=self._SEARCH_MEDIA_TYPES[media_type],
            media_identifier=media_identifier(media_type, result.id),
        )
