# TODO: Validate

from __future__ import annotations

import re
from abc import ABC
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any, ClassVar, Literal, NamedTuple, overload, override

from pydantic import BaseModel, Field
from tminidb.search.multi.models import Result as MultiResult
from tminidb.tv_episode_group.details.models import Episode as TvEpisodeGroupEpisode
from tminidb.tv_episode_group.details.models import Group as TvEpisodeGroup
from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel
from tminidb.tv_season.details.models import Episode as TvSeasonEpisode
from tminidb.tv_season.details.models import TvSeasonDetailsModel

from app.media.media_type import TMDBMediaType
from app.plugins.schemas import (
    PluginSearchResult,
    PluginSearchResults,
    TMDBMediaInfo,
)
from app.titles.models import Title
from app.titles.schemas import WatchProviderOffering
from app.titles.service.watch_providers import record_watch_providers
from app.tmdb_media.service.identifiers import tmdb_title_ids_by_key
from app.tmdb_media.tmdb import (
    chosen_group_id,
    get_media_type_and_season_id,
    get_media_type_and_tmdb_id,
    tmdb_season_key,
    tmdb_title_key,
)
from app.utils import tz_datetime
from plugins.TMDB.files import (
    MoviesDetails,
    MoviesRecommendations,
    MoviesSimilar,
    MoviesWatchProviders,
    SearchMovie,
    SearchMulti,
    SearchTV,
    TVEpisodeGroupsDetails,
    TVSeasonsDetails,
    TVSeasonsWatchProviders,
    TVSeriesDetails,
    TVSeriesEpisodeGroups,
    TVSeriesImages,
    TVSeriesRecommendations,
    TVSeriesSimilar,
    TVSeriesWatchProviders,
)
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.media_type import MediaType


# TODO: Validate
def clean_air_datetime(air_date: str | date | None) -> datetime | None:
    """Return a datetime for the air date and replaces empty strings with None.

    The TMDB API returns an empty string if the date is not known. Converting it to None
    makes it easier to work with."""
    if not isinstance(air_date, date):
        return None
    return tz_datetime.combine(air_date, datetime.min.time())


# TODO: Validate
def runtime_in_seconds(runtime: int | None) -> int | None:
    # If the runtime is not known the API returns None. In all other cases it returns
    # the runtime in minutes.
    return runtime * 60 if runtime else None


# TODO: Validate
def tmdb_url(media_type: str, tmdb_media_id: int) -> str:
    """Return the TMDB URL for the title."""
    return f"https://www.themoviedb.org/{media_type}/{tmdb_media_id}"


# TODO: Validate
def parse_release_year(value: str | date) -> int | None:
    """Return the year of the release date or None if it is not known.

    The TMDB API returns an empty string if the date is not known. Converting it to None
    makes it easier to work with."""
    if isinstance(value, date):
        return value.year
    return None


# TODO: Validate
def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


# TODO: Validate
def image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def thumbnail_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w500", path)


# TODO: Validate
class TMDBSeasonInfo(NamedTuple):
    """Season information from the season details or episode group.

    Normally the data structure of the season details and episode groups are different,
    this class creates a unified representation for both episode groups and season
    details."""

    key: str
    name: str | None
    season_number: int | None
    sort_order: int
    poster_path: str | None
    episodes: Sequence[TvSeasonEpisode | TvEpisodeGroupEpisode]
    uses_episode_group: bool

    # TODO: Validate
    @classmethod
    def from_episode_group(cls, order: int, group: TvEpisodeGroup) -> TMDBSeasonInfo:
        return cls(
            key=tmdb_season_key(TMDBMediaType.tv, order),
            name=group.name,
            # Technically there are no season numbers, but it makes sorting easier if a
            # fake season number is created.
            season_number=order,
            sort_order=order,
            poster_path=None,
            episodes=group.episodes,
            uses_episode_group=True,
        )

    # TODO: Validate
    @classmethod
    def from_season_details(cls, details: TvSeasonDetailsModel) -> TMDBSeasonInfo:
        return cls(
            key=tmdb_season_key(TMDBMediaType.tv, details.id),
            name=details.name,
            season_number=details.season_number,
            sort_order=details.season_number,
            poster_path=details.poster_path,
            episodes=details.episodes,
            uses_episode_group=False,
        )


# TODO: Validate
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
def watch_provider_offerings(watch_providers: Any) -> list[WatchProviderOffering]:  # noqa: ANN401 - One of the strict and optional models of three media types.
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
            logo_url=image_url(provider.logo_path),
            offering_type=offering_type,
        )
        for field_name, region_results in results
        if region_results
        for offering_type in ("flatrate", "ads", "free", "buy", "rent")
        for provider in getattr(region_results, offering_type, None) or []
    ]


# TODO: Validate
class TMDBShared(BasePlugin):
    # TODO: Validate
    def search_multi_file(self, query: str, page: int = 1) -> SearchMulti:
        return self._cached_file(SearchMulti, query, page)

    # TODO: Validate
    def search_movie_file(self, query: str, year: int | None = None) -> SearchMovie:
        return self._cached_file(SearchMovie, query, year)

    # TODO: Validate
    def search_tv_file(self, query: str, year: int | None = None) -> SearchTV:
        return self._cached_file(SearchTV, query, year)

    # TODO: Validate
    def movies_details_file(self, tmdb_movie_id: int) -> MoviesDetails:
        return self._cached_file(MoviesDetails, str(tmdb_movie_id))

    # TODO: Validate
    def tv_series_details_file(self, tmdb_tv_title_id: int) -> TVSeriesDetails:
        return self._cached_file(TVSeriesDetails, tmdb_tv_title_id)

    # TODO: Validate
    def tv_series_images_file(self, tmdb_tv_title_id: int) -> TVSeriesImages:
        return self._cached_file(TVSeriesImages, tmdb_tv_title_id)

    # TODO: Validate
    def tv_series_episode_groups_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesEpisodeGroups:
        return self._cached_file(TVSeriesEpisodeGroups, tmdb_tv_title_id)

    # TODO: Validate
    def tv_episode_groups_details_file(
        self,
        group_id: str,
    ) -> TVEpisodeGroupsDetails:
        return self._cached_file(TVEpisodeGroupsDetails, group_id)

    # TODO: Validate
    def tv_seasons_details_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsDetails:
        return self._cached_file(TVSeasonsDetails, tmdb_tv_title_id, season_number)

    # TODO: Validate
    def movies_recommendations_file(
        self,
        tmdb_movie_id: int,
    ) -> MoviesRecommendations:
        return self._cached_file(MoviesRecommendations, tmdb_movie_id)

    # TODO: Validate
    def tv_series_recommendations_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesRecommendations:
        return self._cached_file(TVSeriesRecommendations, tmdb_tv_title_id)

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
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsWatchProviders:
        return self._cached_file(
            TVSeasonsWatchProviders,
            tmdb_tv_title_id,
            season_number,
        )

    # TODO: Validate
    @classmethod
    @override
    def _link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    def media_info(self, media_identifier: str) -> TMDBMediaInfo:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(media_identifier)
        if media_type == TMDBMediaType.movie:
            movie_details_file = self.movies_details_file(tmdb_media_id)
            movie_providers_file = self.movies_watch_providers_file(tmdb_media_id)
            self._download_if_outdated([movie_details_file, movie_providers_file])
            return TMDBMediaInfo(
                detail=movie_details_file.parsed(),
                watch_providers=movie_providers_file.parsed().results.us,
            )

        series_details_file = self.tv_series_details_file(tmdb_media_id)
        series_providers_file = self.tv_series_watch_providers_file(tmdb_media_id)
        self._download_if_outdated([series_details_file, series_providers_file])
        return TMDBMediaInfo(
            detail=series_details_file.parsed(),
            watch_providers=series_providers_file.parsed().results.us,
        )

    # TODO: Validate
    def _chosen_episode_group(
        self,
        title_key: str,
    ) -> TvEpisodeGroupDetailsModel | None:
        title = Title.get(self.session, self.source, title_key)
        if title and (group_id := chosen_group_id(title.extra)):
            return self.tv_episode_groups_details_file(group_id).parsed()
        return None

    # TODO: Validate
    def chosen_seasons(
        self,
        title_key: str,
    ) -> list[TMDBSeasonInfo]:
        """Return the seasons for the title.

        If the title uses an episode_group the the seasons will be based on the contents
        of TVEpisodeGroupsDetails.

        If the title does not use an episode_group the seasons will be based on the
        contents of TVSeriesDetails.
        """

        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)

        if group := self._chosen_episode_group(title_key):
            return [
                TMDBSeasonInfo.from_episode_group(order, entry)
                for order, entry in enumerate(group.groups)
            ]

        season_files = [
            self.tv_seasons_details_file(
                tmdb_tv_title_id=tmdb_tv_title_id,
                season_number=season.season_number,
            )
            for season in self.tv_series_details_file(tmdb_tv_title_id).parsed().seasons
        ]
        self._download_if_outdated(season_files)
        return [
            TMDBSeasonInfo.from_season_details(season_file.parsed())
            for season_file in season_files
        ]

    # TODO: Validate
    def _native_season_number(self, season_key: str, title_key: str) -> int:
        """Return the number TMDB's own seasons give the season `season_key` names."""
        _, tmdb_tv_season_id = get_media_type_and_season_id(season_key)
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        for season in self.tv_series_details_file(tmdb_tv_title_id).parsed().seasons:
            if season.id == tmdb_tv_season_id:
                return season.season_number
        message = f"{title_key} has no season {season_key}"
        raise ValueError(message)

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
class TMDBSearch(TMDBShared):
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
        attempts: list[tuple[str, int | None]] = [(query, year), (query, None)]
        without_parentheses = re.sub(r"\s*\([^()]*\)", "", query).strip()
        if without_parentheses:
            attempts += [(without_parentheses, year), (without_parentheses, None)]
        attempts = list(dict.fromkeys(attempts))

        search_file = self._fetch_search_file(media_type, *attempts[0])
        for attempt_query, attempt_year in attempts[1:]:
            if search_file.parsed().results:
                return search_file
            search_file = self._fetch_search_file(
                media_type,
                attempt_query,
                attempt_year,
            )
        return search_file

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


# TODO: Validate
class TMDBImporter(TMDBSearch, BaseImporter, ABC):
    # TODO: Validate
    def _record_unmatched_providers(
        self,
        title: Title,
        watch_providers: Any,  # noqa: ANN401 - One of the watch providers models.
    ) -> None:
        """Write down the services carrying `title` that nothing here carries.

        Read on every import rather than once, since which services carry a
        title is the half of this that changes, and the file it is read from is
        downloaded with the rest of the title's either way.
        """
        from app.titles.service.unmatched import (  # noqa: PLC0415
            record_unmatched_providers,
        )

        record_unmatched_providers(
            self.session,
            title,
            watch_provider_names(watch_providers),
        )

    # TODO: Validate
    def _record_watch_providers(
        self,
        title: Title,
        watch_providers: Any,  # noqa: ANN401 - One of the watch providers models.
    ) -> None:
        record_watch_providers(
            self.session,
            title,
            watch_provider_offerings(watch_providers),
        )

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
            existing_title = self._upsert_title(self.source, media_info.title_key)

        return self._import_results(existing_title, media_info)


# TODO: Validate
