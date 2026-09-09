# TODO: Validate
from __future__ import annotations

from datetime import date
from typing import ClassVar, Literal, overload

from pydantic import BaseModel, Field
from tminidb.search.multi.models import Result as MultiResult

from app.canonical_media.tmdb import tmdb_title_key
from app.media.media_type import TMDBMediaType
from app.plugins.schemas import (
    PluginSearchResult,
    PluginSearchResults,
)
from plugins.TMDB.base_files import TMDBBaseFiles
from plugins.TMDB.files import (
    SearchMovie,
    SearchMulti,
    SearchTV,
)
from plugins.TMDB.utils import (
    image_url,
    parse_release_year,
    thumbnail_url,
    tmdb_url,
)


# TODO: Validate
def decode_cursor(cursor: str | None) -> tuple[int, int]:
    if not cursor:
        return 1, 0
    page, _, offset = cursor.partition(":")
    return int(page), int(offset or 0)


# TODO: Validate
def encode_cursor(page: int, offset: int) -> str:
    return f"{page}:{offset}"


# TODO: Validate
class TMDBMovieResult(BaseModel):
    adult: bool
    backdrop_path: str | None
    id: int
    title: str
    original_title: str
    overview: str
    poster_path: str | None
    media_type: Literal["movie"]
    original_language: str
    genre_ids: list[int]
    popularity: float
    release_date: date | str = Field(union_mode="left_to_right")
    softcore: bool
    video: bool
    vote_average: float
    vote_count: int


# TODO: Validate
class TMDBTvShowResult(BaseModel):
    adult: bool
    backdrop_path: str | None
    id: int
    name: str
    original_name: str
    overview: str
    poster_path: str | None
    media_type: Literal["tv"]
    original_language: str
    genre_ids: list[int]
    popularity: float
    first_air_date: date | str = Field(union_mode="left_to_right")
    softcore: bool
    vote_average: float
    vote_count: int
    origin_country: list[str]


# TODO: Validate
def parse_movie_result(result: MultiResult) -> TMDBMovieResult:
    return TMDBMovieResult.model_validate(result, from_attributes=True)


# TODO: Validate
def parse_tv_show_result(result: MultiResult) -> TMDBTvShowResult:
    return TMDBTvShowResult.model_validate(result, from_attributes=True)


# TODO: Validate
class TMDBSearch(TMDBBaseFiles):
    # TODO: Validate
    def first_search_result(
        self,
        name: str,
        media_type: TMDBMediaType | None,
        year: int | None,
    ) -> tuple[TMDBMediaType, int] | None:
        """Return the media_type and the id of the first search result."""
        if media_type:
            results = self._search_for_title(media_type, name, year).parsed().results
            return (media_type, results[0].id) if results else None

        for result in self._search_for_title(None, name, year).parsed().results:
            # SearchMulti returns movies, tv titles, people, collections etc. The results
            # need to be filtered to only movies and tv titles.
            if result.media_type in set(TMDBMediaType):
                return TMDBMediaType(result.media_type), result.id
        return None

    # TODO: Validate
    @overload
    def _search_for_title(
        self,
        media_type: None,
        query: str,
        year: int | None = None,
    ) -> SearchMulti: ...
    # TODO: Validate
    @overload
    def _search_for_title(
        self,
        media_type: TMDBMediaType,
        query: str,
        year: int | None = None,
    ) -> SearchMovie | SearchTV: ...
    # TODO: Validate
    def _search_for_title(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        year: int | None = None,
    ) -> SearchMovie | SearchTV | SearchMulti:
        """Search for a title.

        If no initial match is found, the search is repeated without the year because
        the year is not always reliable."""
        search_file = self._fetch_search_file(media_type, query, year)
        if search_file.parsed().results or not year:
            return search_file
        return self._fetch_search_file(media_type, query, None)

    # TODO: Validate
    def _fetch_search_file(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        year: int | None,
    ) -> SearchMovie | SearchTV | SearchMulti:
        """Fetch the search file from TMDB."""
        search_file: SearchMovie | SearchTV | SearchMulti
        if media_type == TMDBMediaType.movie:
            search_file = self.search_movie_file(query, year)
        elif media_type == TMDBMediaType.tv:
            search_file = self.search_tv_file(query, year)
        else:
            search_file = self.search_multi_file(query)
        search_file.download_if_outdated()
        return search_file

    # A multi search also returns people, who cannot be added to a channel.
    _SEARCH_MEDIA_TYPES: ClassVar = {
        "movie": "Movie",
        "tv": "Series",
    }

    # TODO: Validate
    @classmethod
    def search_page_size(cls) -> int:
        return 20

    # TODO: Validate
    def in_app_search(
        self,
        query: str,
        cursor: str | None = None,
    ) -> PluginSearchResults:
        """Search every title TMDB knows about, whatever it streams on.

        A result's URL is the title's own TMDB page rather than a stream, since
        `import_url` reads that page to find where the title can be watched.
        """
        page, offset = decode_cursor(cursor)
        results: list[PluginSearchResult] = []
        next_cursor: str | None = None

        while len(results) < self.search_page_size():
            search_file = self.search_multi_file(query, page)
            search_file.download_if_outdated()
            parsed = search_file.parsed()
            page_matches = [
                self._search_result(result)
                for result in parsed.results
                if result.media_type in self._SEARCH_MEDIA_TYPES
            ]
            if not page_matches:
                next_cursor = None
                break

            matches = page_matches[offset:]
            wanted = self.search_page_size() - len(results)
            results.extend(matches[:wanted])
            if len(matches) > wanted:
                next_cursor = encode_cursor(page, offset + wanted)
                break

            page += 1
            offset = 0
            if page > parsed.total_pages:
                next_cursor = None
                break
            next_cursor = encode_cursor(page, 0)

        return PluginSearchResults(results=results, next_cursor=next_cursor)

    # TODO: Validate
    def _search_result(self, result: MultiResult) -> PluginSearchResult:
        """Return a PluginSearchResult from a TMDB search result."""

        title: str
        media_type: TMDBMediaType
        if result.media_type == TMDBMediaType.movie:
            movie = parse_movie_result(result)
            media_type = TMDBMediaType.movie
            title = movie.title or movie.original_title
            year = parse_release_year(movie.release_date)
        else:
            tv_show = parse_tv_show_result(result)
            media_type = TMDBMediaType.tv
            title = tv_show.name or tv_show.original_name
            year = parse_release_year(tv_show.first_air_date)

        return PluginSearchResult(
            title=title,
            url=tmdb_url(media_type, result.id),
            year=year,
            image_url=thumbnail_url(result.poster_path)
            or image_url(result.backdrop_path),
            media_type=self._SEARCH_MEDIA_TYPES[media_type],
            media_identifier=tmdb_title_key(media_type, result.id),
        )
