# TODO: Validate

from __future__ import annotations

import re
from abc import ABC
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, ClassVar, Literal, override

from pydantic import BaseModel, Field
from tminidb.search.multi.models import Result as MultiResult

from app.media.media_type import TMDBMediaType
from app.plugins.identifiers import TMDB_VIDEOS_SOURCE_KEY
from app.plugins.schemas import (
    PluginSearchResult,
    PluginSearchResults,
    SearchWatchProvider,
    SearchWatchProviders,
    TMDBMediaInfo,
)
from app.titles.models import Title
from app.titles.schemas import WatchProviderOffering
from app.titles.service.watch_providers import record_watch_providers
from app.tmdb_media.service.identifiers import tmdb_title_ids_by_key
from app.tmdb_media.tmdb import (
    get_media_type_and_tmdb_id,
    tmdb_title_key,
)
from app.utils import tz_datetime
from plugins.TMDB.constants import MOVIE_URL_REGEX, TV_URL_REGEX
from plugins.TMDB.files import (
    MoviesDetails,
    MoviesKeywords,
    MoviesSimilar,
    MoviesWatchProviders,
    SearchMulti,
    TVSeriesDetails,
    TVSeriesKeywords,
    TVSeriesSimilar,
    TVSeriesWatchProviders,
)
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.update_at import set_air_date_update_at
from plugins.utils.base_plugin.upserter import BaseUpserter


# TODO: Validate
class TMDBShared(BasePluginCore):
    # TODO: Validate
    def movies_details_file(self, tmdb_movie_id: int) -> MoviesDetails:
        return self._cached_file(MoviesDetails, str(tmdb_movie_id))

    # TODO: Validate
    def tv_series_details_file(self, tmdb_tv_title_id: int) -> TVSeriesDetails:
        return self._cached_file(TVSeriesDetails, tmdb_tv_title_id)

    # TODO: Validate
    def movies_similar_file(self, tmdb_movie_id: int) -> MoviesSimilar:
        return self._cached_file(MoviesSimilar, tmdb_movie_id)

    # TODO: Validate
    def tv_series_similar_file(self, tmdb_tv_title_id: int) -> TVSeriesSimilar:
        return self._cached_file(TVSeriesSimilar, tmdb_tv_title_id)

    # TODO: Validate
    def movies_watch_providers_file(self, tmdb_movie_id: int) -> MoviesWatchProviders:
        return self._cached_file(MoviesWatchProviders, tmdb_movie_id)

    # TODO: Validate
    def tv_series_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesWatchProviders:
        return self._cached_file(TVSeriesWatchProviders, tmdb_tv_title_id)

    # TODO: Validate
    def details_file(self, title_key: str) -> MoviesDetails | TVSeriesDetails:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(title_key)
        if media_type == TMDBMediaType.movie:
            return self.movies_details_file(tmdb_media_id)
        return self.tv_series_details_file(tmdb_media_id)

    # TODO: Validate
    @override
    def _channel_name(self, topic_prefix: str) -> str:
        return topic_prefix

    # TODO: Validate
    @classmethod
    @override
    def _link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    @staticmethod
    def _image_url(base_url: str, path: str | None) -> str | None:
        return f"{base_url}{path}" if path else None

    # TODO: Validate
    @classmethod
    def image_url(cls, path: str | None) -> str | None:
        return cls._image_url("https://image.tmdb.org/t/p/original", path)

    # TODO: Validate
    @staticmethod
    def tmdb_url(media_type: str, tmdb_media_id: int) -> str:
        """Return the TMDB URL for the title."""
        return f"https://www.themoviedb.org/{media_type}/{tmdb_media_id}"

    # TODO: Validate
    @staticmethod
    def parse_release_year(value: str | date) -> int | None:
        """Return the year of the release date or None if it is not known.

        The TMDB API returns an empty string if the date is not known. Converting it to None
        makes it easier to work with."""
        if isinstance(value, date):
            return value.year
        return None

    # TODO: Validate
    @classmethod
    def thumbnail_url(cls, path: str | None) -> str | None:
        return cls._image_url("https://image.tmdb.org/t/p/w500", path)

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "TMDB"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.themoviedb.org/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "themoviedb.org"

    # TODO: Validate
    def movies_keywords_file(self, tmdb_movie_id: int) -> MoviesKeywords:
        return self._cached_file(MoviesKeywords, tmdb_movie_id)

    # TODO: Validate
    def tv_series_keywords_file(self, tmdb_tv_title_id: int) -> TVSeriesKeywords:
        return self._cached_file(TVSeriesKeywords, tmdb_tv_title_id)

    # TODO: Validate
    def keyword_names(self, title_key: str) -> list[str]:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(title_key)
        if media_type == TMDBMediaType.movie:
            movie_keywords_file = self.movies_keywords_file(tmdb_media_id)
            return [keyword.name for keyword in movie_keywords_file.parsed().keywords]
        series_keywords_file = self.tv_series_keywords_file(tmdb_media_id)
        return [keyword.name for keyword in series_keywords_file.parsed().results]

    # TODO: Validate
    def production_company_names(self, title_key: str) -> list[str]:
        details_file = self.details_file(title_key)
        return [company.name for company in details_file.parsed().production_companies]

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        self.set_title_tag_channels(
            title,
            [
                *(
                    " ".join(
                        word[:1].upper() + word[1:] for word in keyword_name.split(" ")
                    )
                    for keyword_name in self.keyword_names(title.key)
                ),
                *(
                    f"Produced by {company_name}"
                    for company_name in self.production_company_names(title.key)
                ),
            ],
        )


# TODO: Validate
class TMDBPluginShared(TMDBShared):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TV_URL_REGEX)

    # TODO: Validate
    @override
    def title_key_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + MOVIE_URL_REGEX, url):
            return tmdb_title_key(TMDBMediaType.movie, int(match.group("title_key")))
        if match := re.match(domain_regex + TV_URL_REGEX, url):
            return tmdb_title_key(TMDBMediaType.tv, int(match.group("title_key")))

        msg = f"No title key in {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)


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
class TMDBSearch(TMDBShared):
    # TODO: Validate
    def search_multi_file(self, query: str, page: int = 1) -> SearchMulti:
        return self._cached_file(SearchMulti, query, page)

    # TODO: Validate
    def _download_search_multi_file(self, query: str, page: int) -> None:
        self._download_if_outdated([self.search_multi_file(query, page)])

    # A multi search also returns people, who cannot be added to a channel.
    _SEARCH_MEDIA_TYPES: ClassVar = {
        "movie": MediaType.movie,
        "tv": MediaType.series,
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
        page, offset = self.decode_cursor(cursor)
        results: list[PluginSearchResult] = []
        next_cursor: str | None = None

        while len(results) < self.search_page_size():
            self._download_search_multi_file(query, page)
            parsed = self.search_multi_file(query, page).parsed()
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
                next_cursor = self.encode_cursor(page, offset + wanted)
                break

            page += 1
            offset = 0
            if page > parsed.total_pages:
                next_cursor = None
                break
            next_cursor = self.encode_cursor(page, 0)

        self._attach_tmdb_title_ids(results)
        return PluginSearchResults(results=results, next_cursor=next_cursor)

    # TODO: Validate
    def _attach_tmdb_title_ids(self, results: list[PluginSearchResult]) -> None:
        ids_by_key = tmdb_title_ids_by_key(
            self.session,
            {result.media_identifier for result in results if result.media_identifier},
        )
        for result in results:
            tmdb_title_ids = ids_by_key.get(result.media_identifier or "")
            if tmdb_title_ids:
                result.tmdb_title_id = sorted(tmdb_title_ids)[0]

    # TODO: Validate
    def _search_result(self, result: MultiResult) -> PluginSearchResult:
        """Return a PluginSearchResult from a TMDB search result."""

        title: str
        media_type: TMDBMediaType
        if result.media_type == TMDBMediaType.movie:
            movie = self.parse_movie_result(result)
            media_type = TMDBMediaType.movie
            title = movie.title or movie.original_title
            year = self.parse_release_year(movie.release_date)
        else:
            tv_show = self.parse_tv_show_result(result)
            media_type = TMDBMediaType.tv
            title = tv_show.name or tv_show.original_name
            year = self.parse_release_year(tv_show.first_air_date)

        return PluginSearchResult(
            title=title,
            url=self.tmdb_url(media_type, result.id),
            year=year,
            image_url=self.thumbnail_url(result.poster_path)
            or self.image_url(result.backdrop_path),
            media_type=self._SEARCH_MEDIA_TYPES[media_type],
            media_identifier=tmdb_title_key(media_type, result.id),
        )

    # TODO: Validate
    @staticmethod
    def decode_cursor(cursor: str | None) -> tuple[int, int]:
        if not cursor:
            return 1, 0
        page, _, offset = cursor.partition(":")
        return int(page), int(offset or 0)

    # TODO: Validate
    @staticmethod
    def encode_cursor(page: int, offset: int) -> str:
        return f"{page}:{offset}"

    # TODO: Validate
    @staticmethod
    def parse_movie_result(result: MultiResult) -> TMDBMovieResult:
        return TMDBMovieResult.model_validate(result, from_attributes=True)

    # TODO: Validate
    @staticmethod
    def parse_tv_show_result(result: MultiResult) -> TMDBTvShowResult:
        return TMDBTvShowResult.model_validate(result, from_attributes=True)

    # TODO: Validate
    def title_info(self, media_identifier: str) -> TMDBMediaInfo:
        # This function is called when search results are shown. This requires showing
        # titles that are not on the database so additional downloads may be required.
        self._download_if_outdated(
            [
                self.details_file(media_identifier),
                self._watch_providers_file(media_identifier),
            ],
        )
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(media_identifier)
        if media_type == TMDBMediaType.movie:
            movie_details_file = self.movies_details_file(tmdb_media_id)
            movie_providers_file = self.movies_watch_providers_file(tmdb_media_id)
            return TMDBMediaInfo(
                detail=movie_details_file.parsed(),
                watch_providers=movie_providers_file.parsed().results.us,
            )

        series_details_file = self.tv_series_details_file(tmdb_media_id)
        series_providers_file = self.tv_series_watch_providers_file(tmdb_media_id)
        return TMDBMediaInfo(
            detail=series_details_file.parsed(),
            watch_providers=series_providers_file.parsed().results.us,
        )

    # TODO: Validate
    def _watch_providers_file(
        self,
        media_identifier: str,
    ) -> MoviesWatchProviders | TVSeriesWatchProviders:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(media_identifier)
        if media_type == TMDBMediaType.movie:
            return self.movies_watch_providers_file(tmdb_media_id)
        return self.tv_series_watch_providers_file(tmdb_media_id)

    # TODO: Validate
    def search_watch_providers(
        self,
        media_identifiers: Sequence[str],
    ) -> SearchWatchProviders:
        """Return the streaming services each search result can be watched on.

        Read on its own rather than as part of the search because it is a request
        per result, and a page of results is worth showing before they arrive.
        """
        unique_media_identifiers = list(dict.fromkeys(media_identifiers))
        # This function is called when search results are shown. This requires showing
        # titles that are not on the database so additional downloads may be required.
        self._download_if_outdated(
            [
                self._watch_providers_file(media_identifier)
                for media_identifier in unique_media_identifiers
            ],
        )
        providers: dict[str, list[SearchWatchProvider]] = {}
        for media_identifier in unique_media_identifiers:
            providers_file = self._watch_providers_file(media_identifier)
            providers[media_identifier] = self.streaming_watch_providers(
                providers_file.parsed(),
            )
        return SearchWatchProviders(providers=providers)

    # TODO: Validate
    @classmethod
    def streaming_watch_providers(
        cls,
        watch_providers: Any,  # noqa: ANN401 - One of the strict and optional models of three media types.
    ) -> list[SearchWatchProvider]:
        us_results = watch_providers.results.us
        if not us_results:
            return []
        providers: dict[int, SearchWatchProvider] = {}
        for offering_type in ("flatrate", "ads", "free"):
            for provider in getattr(us_results, offering_type, None) or []:
                providers.setdefault(
                    provider.provider_id,
                    SearchWatchProvider(
                        tmdb_provider_id=provider.provider_id,
                        provider_name=provider.provider_name,
                        logo_url=cls.image_url(provider.logo_path),
                    ),
                )
        return list(providers.values())


# TODO: Validate
class TMDBImporter(TMDBShared, BaseUpserter, ABC):
    # TODO: Validate
    def _set_linked_titles_update_at(self, tmdb_title: Title) -> None:
        air_dates = [
            episode.air_date
            for season in tmdb_title.seasons
            for episode in season.episodes
            if episode.air_date
        ]
        for link in tmdb_title.linked_title_links:
            if link.linked_title.source.key == TMDB_VIDEOS_SOURCE_KEY:
                continue
            set_air_date_update_at(link.linked_title, air_dates)

    # TODO: Validate
    def _record_unmatched_providers(
        self,
        title: Title,
        watch_providers: Any,  # noqa: ANN401 - One of the watch providers models.
    ) -> None:
        """Write down the services that offer `title` and that nothing here has.

        Read on every import rather than once, since which services offer a
        title is the half of this that changes, and the file it is read from is
        downloaded with the rest of the title's either way.
        """
        from app.titles.service.unmatched import (  # noqa: PLC0415
            record_unmatched_providers,
        )

        record_unmatched_providers(
            self.session,
            title,
            self.watch_provider_names(watch_providers),
        )

    # TODO: Validate
    def record_providers(
        self,
        title: Title,
        watch_providers: Any,  # noqa: ANN401
    ) -> None:
        self._record_unmatched_providers(title, watch_providers)
        self._record_watch_providers(title, watch_providers)

    # TODO: Validate
    def _record_watch_providers(
        self,
        title: Title,
        watch_providers: Any,  # noqa: ANN401 - One of the watch providers models.
    ) -> None:
        record_watch_providers(
            self.session,
            title,
            self.watch_provider_offerings(watch_providers),
        )

    # TODO: Validate
    @staticmethod
    def watch_provider_names(watch_providers: Any) -> set[str]:  # noqa: ANN401 - One of the strict and optional models of three media types.
        us_results = watch_providers.results.us
        if not us_results:
            return set()
        return {
            provider.provider_name
            for offering in ("flatrate", "ads", "free", "buy", "rent")
            for provider in getattr(us_results, offering, None) or []
        }

    # TODO: Validate
    @classmethod
    def watch_provider_offerings(
        cls,
        watch_providers: Any,  # noqa: ANN401 - One of the strict and optional models of three media types.
    ) -> list[WatchProviderOffering]:
        results = watch_providers.results
        if not results:
            return []
        region_codes = {
            field_name: field.alias or field_name.upper()
            for field_name, field in type(results).model_fields.items()
        }
        return [
            WatchProviderOffering(
                region=region_codes[field_name],
                tmdb_provider_id=provider.provider_id,
                provider_name=provider.provider_name,
                logo_url=cls.image_url(provider.logo_path),
                offering_type=offering_type,
            )
            for field_name, region_results in results
            if region_results
            for offering_type in ("flatrate", "ads", "free", "buy", "rent")
            for provider in getattr(region_results, offering_type, None) or []
        ]

    # TODO: Validate
    @staticmethod
    def clean_air_datetime(air_date: str | date | None) -> datetime | None:
        """Return a datetime for the air date and replaces empty strings with None.

        The TMDB API returns an empty string if the date is not known. Converting it to None
        makes it easier to work with."""
        if not isinstance(air_date, date):
            return None
        return tz_datetime.combine(air_date, datetime.min.time())

    # TODO: Validate
    @staticmethod
    def runtime_in_seconds(runtime: int | None) -> int | None:
        # If the runtime is not known the API returns None. In all other cases it returns
        # the runtime in minutes.
        return runtime * 60 if runtime else None

    # TODO: Validate
    @override
    def _update_and_upsert_title(self, title: Title) -> None:
        # Download just details_file first to check for deleted entries. Downloading all
        # the files would be unnecessary if the title has been deleted.
        details_file = self.details_file(title.key)
        self._download_if_outdated([details_file], title.update_at)
        if details_file.record_content is None:
            self._delete_title(title)
            return
        super()._update_and_upsert_title(title)

    # TODO: Validate
    def _delete_title(self, title: Title) -> None:
        from app.titles.service.linking import (  # noqa: PLC0415
            unlink_titles_from_tmdb_title,
        )

        unlink_titles_from_tmdb_title(self.session, title)
        title.soft_delete()
        self.add_title_to_channels(title)

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.parse_url(url)
        existing_title = self._preload_title(
            title=media_info.title_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_title:
            self._preload_and_download_files(media_info.title_key)
            with self.session.no_autoflush:
                existing_title = self._upsert_title(self.source, media_info.title_key)
            self.add_title_to_channels(existing_title)

        return self._import_results(existing_title, media_info)


# TODO: Validate
