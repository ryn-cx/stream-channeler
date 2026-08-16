# TODO: Validate
from collections.abc import Sequence
from datetime import date, datetime
from functools import cache
from http import HTTPStatus
from typing import Any, ClassVar, Literal, NamedTuple, overload, override

from pydantic import BaseModel
from sqlmodel import Session
from tminidb import TMiniDB
from tminidb.exceptions import HTTPError
from tminidb.movie_details.models import MovieDetailsModel
from tminidb.movie_watch_providers.models import MovieWatchProvidersModel
from tminidb.search_movie.models import SearchMovieModel
from tminidb.search_multi.models import SearchMultiModel
from tminidb.search_tv.models import SearchTvModel
from tminidb.tv_episode_details.models import TvEpisodeDetailsModel
from tminidb.tv_episode_group_details.models import TvEpisodeGroupDetailsModel
from tminidb.tv_episode_translations.models import TvEpisodeTranslationsModel
from tminidb.tv_season_details.models import TvSeasonDetailsModel
from tminidb.tv_series_details.models import TvSeriesDetailsModel
from tminidb.tv_series_episode_groups.models import TvSeriesEpisodeGroupsModel
from tminidb.tv_watch_providers.models import TvWatchProvidersModel

from app.config import settings
from app.media.media_type import MediaType
from app.plugins.models import Plugin
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB.episode_groups import chosen_group_id
from plugins.TMDB.keys import (
    parse_season_key,
    parse_show_key,
    season_key,
)
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, HTMLFile
from plugins.utils.base_plugin.plugin import BasePlugin
from plugins.utils.get_around_client import get_around_client

TMDB_DOMAIN = "themoviedb.org"


# TODO: Validate
def title_page_url(media_type: str, tmdb_id: int) -> str:
    """Return the themoviedb.org page a user would visit for a title."""
    return f"https://www.{TMDB_DOMAIN}/{media_type}/{tmdb_id}?language=en-US"


_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w342"
_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/original"
_STILL_BASE_URL = "https://image.tmdb.org/t/p/original"
_LOGO_BASE_URL = "https://image.tmdb.org/t/p/w92"


# TODO: Validate
@cache
def tminidb_client() -> TMiniDB:
    # TMDB is a public API, so a direct client is used rather than the get-around
    # proxy. The read access token is stored in the keyring.
    return TMiniDB(access_token=settings.TMDB_API_READ_TOKEN)


# TODO: Validate
def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


# TODO: Validate
def release_year(value: str | date | None) -> int | None:
    if isinstance(value, date):
        return value.year
    return int(value[:4]) if value else None


# TODO: Validate
def poster_image_url(path: str | None) -> str | None:
    return _image_url(_POSTER_BASE_URL, path)


# TODO: Validate
def backdrop_image_url(path: str | None) -> str | None:
    return _image_url(_BACKDROP_BASE_URL, path)


# TODO: Validate
def still_image_url(path: str | None) -> str | None:
    return _image_url(_STILL_BASE_URL, path)


# TODO: Validate
def logo_image_url(path: str | None) -> str | None:
    return _image_url(_LOGO_BASE_URL, path)


# TODO: Validate
def duration_seconds(runtime: int | None) -> int | None:
    return runtime * 60 if runtime else None


# TODO: Validate
def air_datetime(air_date: date | None) -> datetime | None:
    # A date TMDB does not have yet comes back as an empty string rather than
    # being left out, which the generated model types as a `date` but passes
    # along as it arrived.
    if not air_date:
        return None
    return tz_datetime.combine(air_date, datetime.min.time())


# TODO: Validate
class _TMDBEndpointFile[T: BaseModel](GAPIJSON[T]):
    """TMDB endpoint file."""

    API_ENDPOINT: ClassVar[Any]

    # Occurs when a user puts in a URL for a title TMDB does not have, and when a
    # season or an episode is asked for by a number the title does not run to.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return (
            isinstance(error, HTTPError) and error.status_code == HTTPStatus.NOT_FOUND
        )


# TODO: Validate
class _TMDBIdEndpointFile[T: BaseModel](_TMDBEndpointFile[T]):
    """A TMDB file the API looks up by a title's numeric id.

    A file is keyed by a string, but TMDB checks that the response it hands back
    is for the id that was asked for, and the id it read out of the response is a
    number. A string never matches one, so the id is passed as what it is.
    """

    # TODO: Validate
    @override
    def _get(self) -> T:
        return self.API_ENDPOINT.download_and_parse(int(self.unique_identifier))


# TODO: Validate
class MovieDetails(_TMDBIdEndpointFile[MovieDetailsModel]):
    """Movie details file."""

    API_ENDPOINT = tminidb_client().movie_details


# TODO: Validate
class TvSeriesDetails(_TMDBIdEndpointFile[TvSeriesDetailsModel]):
    """TV series details file."""

    API_ENDPOINT = tminidb_client().tv_series_details


# TODO: Validate
class MovieWatchProviders(_TMDBIdEndpointFile[MovieWatchProvidersModel]):
    """Movie watch providers file."""

    API_ENDPOINT = tminidb_client().movie_watch_providers


# TODO: Validate
class TvWatchProviders(_TMDBIdEndpointFile[TvWatchProvidersModel]):
    """TV watch providers file."""

    API_ENDPOINT = tminidb_client().tv_watch_providers


# TODO: Validate
class ShowDetail(_TMDBIdEndpointFile[TvSeriesDetailsModel]):
    """Show detail file.

    The seasons and episodes under a title are reached through
    `_season_keys_from_file` and `_episode_keys_from_file`, so this file only
    carries the title itself.
    """

    API_ENDPOINT = tminidb_client().tv_series_details


# TODO: Validate
class EpisodeGroups(_TMDBIdEndpointFile[TvSeriesEpisodeGroupsModel]):
    """Every episode order TMDB holds for a title, beside the title's own.

    Only what each order is called and how big it is - the episodes an order
    puts where are `EpisodeGroupDetail`, one file per order, since a title with
    six orders is six files nobody wants downloaded to read a list of names.
    """

    API_ENDPOINT = tminidb_client().tv_series_episode_groups


# TODO: Validate
class EpisodeGroupDetail(_TMDBEndpointFile[TvEpisodeGroupDetailsModel]):
    """One episode order, and the episodes each of its groups holds.

    Keyed by the order's own id rather than by the title's, because that is what
    TMDB looks it up by and one order belongs to one title anyway. The id is a
    string of TMDB's own making rather than a number, so it is passed along as
    it came rather than through `_TMDBIdEndpointFile`.
    """

    API_ENDPOINT = tminidb_client().tv_episode_group_details

    # TODO: Validate
    @override
    def _get(self) -> TvEpisodeGroupDetailsModel:
        return self.API_ENDPOINT.download_and_parse(self.unique_identifier)


# TODO: Validate
class SeasonDetail(_TMDBEndpointFile[TvSeasonDetailsModel]):
    """Season detail file."""

    API_ENDPOINT = tminidb_client().tv_season_details

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{tmdb_show_id}/{season_number}")

    # TODO: Validate
    @override
    def _get(self) -> TvSeasonDetailsModel:
        return self.API_ENDPOINT.download_and_parse(
            self.tmdb_show_id,
            self.season_number,
        )


# TODO: Validate
class EpisodeDetail(_TMDBEndpointFile[TvEpisodeDetailsModel]):
    """Episode detail file."""

    API_ENDPOINT = tminidb_client().tv_episode_details

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        self.episode_number = episode_number
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{season_number}/{episode_number}",
        )

    # TODO: Validate
    @override
    def _get(self) -> TvEpisodeDetailsModel:
        return self.API_ENDPOINT.download_and_parse(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


# TODO: Validate
class EpisodeTranslations(_TMDBEndpointFile[TvEpisodeTranslationsModel]):
    """Every language's name for a single episode."""

    API_ENDPOINT = tminidb_client().tv_episode_translations

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        self.episode_number = episode_number
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{season_number}/{episode_number}",
        )

    # TODO: Validate
    @override
    def _get(self) -> TvEpisodeTranslationsModel:
        return self.API_ENDPOINT.download_and_parse(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


# TODO: Validate
class MultiSearch(_TMDBEndpointFile[SearchMultiModel]):
    """Multi search file."""

    API_ENDPOINT = tminidb_client().search_multi

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        page: int = 1,
    ) -> None:
        self.query = query
        self.page = page
        super().__init__(session, plugin, query if page == 1 else f"{query}/{page}")

    # TODO: Validate
    @override
    def _get(self) -> SearchMultiModel:
        return self.API_ENDPOINT.download_and_parse(self.query, page=self.page)


# TODO: Validate
class TitlePage(HTMLFile):
    """The themoviedb.org web page for a single title.

    Downloaded to tell a URL naming a title TMDB holds from one naming nothing,
    which is what a pasted address is checked against.
    """

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        media_type: str,
        tmdb_id: int,
    ) -> None:
        self.media_type = media_type
        self.tmdb_id = tmdb_id
        super().__init__(session, plugin, f"{media_type}/{tmdb_id}")

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            url = title_page_url(self.media_type, self.tmdb_id)
            response = get_around_client().get(url, follow_redirects=True)
            if response.status_code == HTTPStatus.NOT_FOUND:
                self.write(None)
                return
            response.raise_for_status()
            self.write(response.text)


# TODO: Validate
class MovieSearch(_TMDBEndpointFile[SearchMovieModel]):
    """Movie search file."""

    API_ENDPOINT = tminidb_client().search_movie

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        year: int | None = None,
    ) -> None:
        self.query = query
        self.year = year
        super().__init__(session, plugin, query if year is None else f"{query}/{year}")

    # TODO: Validate
    @override
    def _get(self) -> SearchMovieModel:
        year = None if self.year is None else str(self.year)
        return self.API_ENDPOINT.download_and_parse(self.query, year=year)


# TODO: Validate
class TvSearch(_TMDBEndpointFile[SearchTvModel]):
    """TV search file."""

    API_ENDPOINT = tminidb_client().search_tv

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        year: int | None = None,
    ) -> None:
        self.query = query
        self.year = year
        super().__init__(session, plugin, query if year is None else f"{query}/{year}")

    # TODO: Validate
    @override
    def _get(self) -> SearchTvModel:
        return self.API_ENDPOINT.download_and_parse(self.query, year=self.year)


# TODO: Validate
class EpisodeSource(NamedTuple):
    """One episode of a season, and the number the order gives it."""

    number: int
    entry: Any


# TODO: Validate
class SeasonSource(NamedTuple):
    """One season of a title, however the title is being read.

    The two ways of reading a series - TMDB's own seasons and a chosen episode
    order - answer with different files holding different shapes, and everything
    that writes a season wants the same handful of things out of either. So both
    are read into this and nothing downstream asks which it was.
    """

    key: str
    name: str | None
    season_number: int
    poster_path: str | None
    episodes: list[EpisodeSource]


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    # TODO: Validate
    def multi_search_file(self, query: str, page: int = 1) -> MultiSearch:
        """Returns MultiSearch file."""
        return self._file(MultiSearch, query, page)

    # TODO: Validate
    def title_page_file(self, media_type: str, tmdb_id: int) -> TitlePage:
        """Returns TitlePage file."""
        return self._file(TitlePage, media_type, tmdb_id)

    # TODO: Validate
    def movie_search_file(self, query: str, year: int | None = None) -> MovieSearch:
        """Returns MovieSearch file."""
        return self._file(MovieSearch, query, year)

    # TODO: Validate
    def tv_search_file(self, query: str, year: int | None = None) -> TvSearch:
        """Returns TvSearch file."""
        return self._file(TvSearch, query, year)

    # TODO: Validate
    def movie_detail_file(self, tmdb_id: int) -> MovieDetails:
        """Returns MovieDetails file."""
        return self._file(MovieDetails, str(tmdb_id))

    # TODO: Validate
    def show_detail_file(self, tmdb_id: int) -> ShowDetail:
        """Returns ShowDetail file."""
        return self._file(ShowDetail, tmdb_id)

    # TODO: Validate
    def episode_groups_file(self, tmdb_id: int) -> EpisodeGroups:
        """Returns the EpisodeGroups file for a title."""
        return self._file(EpisodeGroups, tmdb_id)

    # TODO: Validate
    def episode_group_detail_file(self, group_id: str) -> EpisodeGroupDetail:
        """Returns the EpisodeGroupDetail file for one episode order."""
        return self._file(EpisodeGroupDetail, group_id)

    # TODO: Validate
    def season_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
    ) -> SeasonDetail:
        """Returns SeasonDetail file."""
        return self._file(SeasonDetail, tmdb_show_id, season_number)

    # TODO: Validate
    def episode_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> EpisodeDetail:
        """Returns EpisodeDetail file."""
        return self._file(
            EpisodeDetail,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    # TODO: Validate
    def episode_translations_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> EpisodeTranslations:
        """Returns EpisodeTranslations file."""
        return self._file(
            EpisodeTranslations,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    # TODO: Validate
    def tv_detail_file(self, tmdb_id: int) -> TvSeriesDetails:
        """Returns TvSeriesDetails file."""
        return self._file(TvSeriesDetails, str(tmdb_id))

    # TODO: Validate
    def movie_watch_providers_file(self, tmdb_id: int) -> MovieWatchProviders:
        """Returns MovieWatchProviders file."""
        return self._file(MovieWatchProviders, str(tmdb_id))

    # TODO: Validate
    def tv_watch_providers_file(self, tmdb_id: int) -> TvWatchProviders:
        """Returns TvWatchProviders file."""
        return self._file(TvWatchProviders, str(tmdb_id))

    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: Literal[MediaType.movie],
        tmdb_id: int,
    ) -> MovieDetails: ...
    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: Literal[MediaType.tv],
        tmdb_id: int,
    ) -> TvSeriesDetails: ...
    # TODO: Validate
    @overload
    def media_detail_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieDetails | TvSeriesDetails: ...
    # TODO: Validate
    def media_detail_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieDetails | TvSeriesDetails:
        """Returns MovieDetails or TvSeriesDetails file."""
        if media_type == MediaType.movie:
            return self.movie_detail_file(tmdb_id)
        return self.tv_detail_file(tmdb_id)

    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: Literal[MediaType.movie],
        tmdb_id: int,
    ) -> MovieWatchProviders: ...
    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: Literal[MediaType.tv],
        tmdb_id: int,
    ) -> TvWatchProviders: ...
    # TODO: Validate
    @overload
    def watch_providers_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders: ...
    # TODO: Validate
    def watch_providers_file(
        self,
        media_type: MediaType,
        tmdb_id: int,
    ) -> MovieWatchProviders | TvWatchProviders:
        """Returns MovieWatchProviders or TvWatchProviders file."""
        if media_type == MediaType.movie:
            return self.movie_watch_providers_file(tmdb_id)
        return self.tv_watch_providers_file(tmdb_id)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]

        # `ShowDetail` downloads every season and episode file along with itself.
        # Every episode order comes down too, and the episodes of every one of
        # them, so whichever order is chosen later is already here to be read
        # rather than waiting on an import of its own.
        groups_file = self.episode_groups_file(tmdb_id)
        # Downloaded here rather than left to the caller, because what it lists
        # is what says which order files there are, and a list of files cannot
        # name them before it has been read.
        groups_file.download_if_outdated()
        return [
            self.show_detail_file(tmdb_id),
            groups_file,
            *(
                self.episode_group_detail_file(option.id)
                for option in self._episode_group_options(tmdb_id)
            ),
        ]

    # TODO: Validate
    def _episode_group_options(self, tmdb_id: int) -> Sequence[Any]:
        """Return every episode order TMDB lists for a title.

        A title TMDB holds no orders for, and one the endpoint has nothing to
        say about at all, both read as none rather than raising: an order is
        something a title may simply not have.
        """
        groups_file = self.episode_groups_file(tmdb_id)
        if not groups_file.database_record.content:
            return []
        return groups_file.parsed().results

    # TODO: Validate
    def _chosen_group_id(self, show_key: str) -> str | None:
        """Return the episode order this title is read in, where one was chosen.

        Read off the stored `Show` rather than off a file, since the choice is a
        `User`'s and nothing TMDB says. A title being imported for the first time
        has no row to have chosen anything yet, which reads as TMDB's own order.
        """
        show = Show.get(self.session, self.source, show_key)
        return chosen_group_id(show.extra) if show else None

    # TODO: Validate
    def _chosen_group(self, show_key: str) -> TvEpisodeGroupDetailsModel | None:
        """Return the chosen episode order itself, where there is one."""
        group_id = self._chosen_group_id(show_key)
        if group_id is None:
            return None
        return self.episode_group_detail_file(group_id).parsed()

    # TODO: Validate
    def series_seasons(self, show_key: str) -> list[SeasonSource]:
        """Return the seasons of a series, in whichever order it is read in.

        A chosen order replaces the title's own outright: its groups are the
        seasons and its episodes are numbered by where the order puts them, not
        by where TMDB's own seasons did. The episodes keep their own ids either
        way, so the same episode is the same row whichever order it is read in
        and a title changing order moves its episodes rather than replacing them.
        """
        _, tmdb_id = parse_show_key(show_key)
        group = self._chosen_group(show_key)
        if group is not None:
            return [
                SeasonSource(
                    key=season_key(MediaType.tv, order),
                    name=entry.name,
                    season_number=order + 1,
                    poster_path=None,
                    episodes=[
                        EpisodeSource(number=number, entry=episode)
                        for number, episode in enumerate(entry.episodes, start=1)
                    ],
                )
                for order, entry in enumerate(group.groups)
            ]

        seasons: list[SeasonSource] = []
        for season in self.show_detail_file(tmdb_id).parsed().seasons:
            season_file = self.season_detail_file(tmdb_id, season.season_number)
            # Downloaded here rather than left to the caller for the same reason
            # the orders are: what says which seasons a title has is the title's
            # own file, so nothing can name a season file before that has been
            # read, and a title being imported for the first time has none of
            # them stored to be read out of.
            season_file.download_if_outdated()
            # A season the title lists but TMDB has no detail for is stored
            # empty, and an empty file has nothing to read a season out of.
            if not season_file.database_record.content:
                continue
            detail = season_file.parsed()
            seasons.append(
                SeasonSource(
                    key=season_key(MediaType.tv, season.id),
                    name=detail.name,
                    season_number=season.season_number,
                    poster_path=detail.poster_path,
                    episodes=[
                        EpisodeSource(number=episode.episode_number, entry=episode)
                        for episode in detail.episodes
                    ],
                ),
            )
        return seasons

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        group_id = self._chosen_group_id(show_key)
        if group_id is not None:
            return [self.episode_group_detail_file(group_id)]
        return [
            self.season_detail_file(
                tmdb_id,
                self._native_season_number(season_key, show_key),
            ),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the file an episode was read out of, which is its season's.

        A season carries every episode of it, so that one file is where an
        episode's own record comes from and what says how current it is. TMDB
        does hold a file per episode, but nothing here is read from it: what
        wants one - matching a website's episode to TMDB's by name - downloads
        it as it gets there, and naming it here would have every import fetch
        two files an episode for nothing.
        """
        return self._season_files(season_key, show_key)

    # TODO: Validate
    def _native_season_number(self, season_key: str, show_key: str) -> int:
        """Return the number TMDB's own seasons give the season `season_key` names."""
        _, season_tmdb_id = parse_season_key(season_key)
        _, tmdb_id = parse_show_key(show_key)
        for season in self.show_detail_file(tmdb_id).parsed().seasons:
            if season.id == season_tmdb_id:
                return season.season_number
        message = f"{show_key} has no season {season_key}"
        raise ValueError(message)
