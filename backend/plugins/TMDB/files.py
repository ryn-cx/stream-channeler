# TODO: Validate
from collections.abc import Sequence
from datetime import date, timedelta
from functools import cache
from http import HTTPStatus
from typing import (
    Any,
    ClassVar,
    Literal,
    NamedTuple,
    overload,
    override,
)

from sqlmodel import Session, col, select
from tminidb import TMiniDB
from tminidb.changes.tv_series import TvSeriesChanges as TvSeriesChangesEndpoint
from tminidb.changes.tv_series.models import Change, TvSeriesChangesModel
from tminidb.details.movie import Movie as MovieEndpoint
from tminidb.details.movie.models import MovieModel
from tminidb.details.tv_episode import TvEpisode as TvEpisodeEndpoint
from tminidb.details.tv_episode.models import TvEpisodeModel
from tminidb.details.tv_season import TvSeason as TvSeasonEndpoint
from tminidb.details.tv_season.models import Episode, TvSeasonModel
from tminidb.details.tv_series import TvSeries as TvSeriesEndpoint
from tminidb.details.tv_series.models import TvSeriesModel
from tminidb.exceptions import ResourceNotFoundError
from tminidb.search.movie import SearchMovie as SearchMovieEndpoint
from tminidb.search.movie.models import SearchMovieModel
from tminidb.search.multi import SearchMulti as SearchMultiEndpoint
from tminidb.search.multi.models import SearchMultiModel
from tminidb.search.tv import SearchTv as SearchTvEndpoint
from tminidb.search.tv.models import SearchTvModel
from tminidb.tv_episode_group import TvEpisodeGroup as TvEpisodeGroupEndpoint
from tminidb.tv_episode_group.models import Episode as GroupEpisode
from tminidb.tv_episode_group.models import TvEpisodeGroupModel
from tminidb.tv_episode_translations import (
    TvEpisodeTranslations as TvEpisodeTranslationsEndpoint,
)
from tminidb.tv_episode_translations.models import TvEpisodeTranslationsModel
from tminidb.tv_series_episode_groups import (
    TvSeriesEpisodeGroups as TvSeriesEpisodeGroupsEndpoint,
)
from tminidb.tv_series_episode_groups.models import Result as EpisodeGroupSummary
from tminidb.tv_series_episode_groups.models import TvSeriesEpisodeGroupsModel
from tminidb.watch_providers.movie import (
    MovieWatchProviders as MovieWatchProvidersEndpoint,
)
from tminidb.watch_providers.movie.models import MovieWatchProvidersModel
from tminidb.watch_providers.tv_series import (
    TvSeriesWatchProviders as TvSeriesWatchProvidersEndpoint,
)
from tminidb.watch_providers.tv_series.models import TvSeriesWatchProvidersModel

from app.config import settings
from app.files.models import File
from app.media.media_type import MediaType
from app.plugins.models import Plugin
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB.constants import TMDB_DOMAIN
from plugins.TMDB.episode_groups import chosen_group_id
from plugins.TMDB.keys import (
    parse_season_key,
    parse_show_key,
    season_key,
)
from plugins.utils.base_plugin.files import BaseFile, EndpointFile, HTMLFile
from plugins.utils.base_plugin.plugin import BasePlugin
from plugins.utils.get_around_client import get_around_client


@cache
def tminidb() -> TMiniDB:
    return TMiniDB(settings.TMDB_API_READ_TOKEN)


# TODO: Validate
def title_page_url(media_type: str, tmdb_id: int) -> str:
    """Return the themoviedb.org page a user would visit for a title."""
    return f"https://www.{TMDB_DOMAIN}/{media_type}/{tmdb_id}?language=en-US"


# TODO: Validate
class MovieDetails(EndpointFile[MovieModel]):

    API_ENDPOINT: ClassVar[MovieEndpoint] = tminidb().movie

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(int(self.unique_identifier))


# TODO: Validate
class TvSeriesDetails(EndpointFile[TvSeriesModel]):
    """TV series details file."""

    API_ENDPOINT: ClassVar[TvSeriesEndpoint] = tminidb().tv_series

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(int(self.unique_identifier))


# TODO: Validate
class MovieWatchProviders(EndpointFile[MovieWatchProvidersModel]):
    """Movie watch providers file."""

    API_ENDPOINT: ClassVar[MovieWatchProvidersEndpoint] = (
        tminidb().movie_watch_providers
    )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(int(self.unique_identifier))


# TODO: Validate
class TvWatchProviders(EndpointFile[TvSeriesWatchProvidersModel]):
    """TV watch providers file."""

    API_ENDPOINT: ClassVar[TvSeriesWatchProvidersEndpoint] = (
        tminidb().tv_series_watch_providers
    )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(int(self.unique_identifier))


# TODO: Validate
class ShowDetail(EndpointFile[TvSeriesModel]):
    """Show detail file.

    The seasons and episodes under a title are reached through
    `_season_keys_from_file` and `_episode_keys_from_file`, so this file only
    carries the title itself.
    """

    API_ENDPOINT: ClassVar[TvSeriesEndpoint] = tminidb().tv_series

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(int(self.unique_identifier))


# TODO: Validate
class EpisodeGroups(EndpointFile[TvSeriesEpisodeGroupsModel]):
    """Every episode order TMDB holds for a title, beside the title's own.

    Only what each order is called and how big it is - the episodes an order
    puts where are `EpisodeGroupDetail`, one file per order, since a title with
    six orders is six files nobody wants downloaded to read a list of names.
    """

    API_ENDPOINT: ClassVar[TvSeriesEpisodeGroupsEndpoint] = (
        tminidb().tv_series_episode_groups
    )

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(int(self.unique_identifier))


# TODO: Validate
class EpisodeGroupDetail(EndpointFile[TvEpisodeGroupModel]):
    """One episode order, and the episodes each of its groups holds.

    Keyed by the order's own id rather than by the title's, because that is what
    TMDB looks it up by and one order belongs to one title anyway. The id is a
    string of TMDB's own making rather than a number, so it is passed along as
    it came rather than as a number.
    """

    API_ENDPOINT: ClassVar[TvEpisodeGroupEndpoint] = tminidb().tv_episode_group

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class SeasonDetail(EndpointFile[TvSeasonModel]):
    """Season detail file."""

    API_ENDPOINT: ClassVar[TvSeasonEndpoint] = tminidb().tv_season

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

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
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(self.tmdb_show_id, self.season_number)


# TODO: Validate
class EpisodeDetail(EndpointFile[TvEpisodeModel]):
    """Episode detail file."""

    API_ENDPOINT: ClassVar[TvEpisodeEndpoint] = tminidb().tv_episode

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
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


# TODO: Validate
class EpisodeTranslations(EndpointFile[TvEpisodeTranslationsModel]):
    """Every language's name for a single episode."""

    API_ENDPOINT: ClassVar[TvEpisodeTranslationsEndpoint] = (
        tminidb().tv_episode_translations
    )

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

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
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


# TODO: Validate
class ShowChanges(EndpointFile[TvSeriesChangesModel]):
    API_ENDPOINT: ClassVar[TvSeriesChangesEndpoint] = tminidb().tv_series_changes

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        since: date,
        downloaded_to: date,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.since = since
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{downloaded_to.isoformat()}",
        )

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # An end date is asked with as well as a start, because TMDB answers a
        # start on its own with the fortnight after it rather than everything
        # since, and a title left alone for longer than that would have the
        # changes either side of its first fortnight go unread. Asked with both,
        # the endpoint splits the range and merges what each part answers with.
        return self.API_ENDPOINT.download_merged(
            self.tmdb_show_id,
            self.since,
            tz_datetime.now().date(),
        )

    # TODO: Validate
    def changes(self) -> Sequence[Change]:
        if not self.database_record.content:
            return []
        return self.parsed().changes


# TODO: Validate
class MultiSearch(EndpointFile[SearchMultiModel]):
    """Multi search file."""

    API_ENDPOINT: ClassVar[SearchMultiEndpoint] = tminidb().search_multi

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
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(self.query, page=self.page)


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
class MovieSearch(EndpointFile[SearchMovieModel]):
    """Movie search file."""

    API_ENDPOINT: ClassVar[SearchMovieEndpoint] = tminidb().search_movie

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
    def _download_file(self) -> str:
        year = None if self.year is None else str(self.year)
        return self.API_ENDPOINT.download(self.query, year=year)


# TODO: Validate
class TvSearch(EndpointFile[SearchTvModel]):
    """TV search file."""

    API_ENDPOINT: ClassVar[SearchTvEndpoint] = tminidb().search_tv

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
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(self.query, year=self.year)


# TODO: Validate
class EpisodeSource(NamedTuple):
    """One episode of a season, and the number the order gives it."""

    number: int
    entry: Episode | GroupEpisode


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
        """Return MultiSearch file."""
        return self._file(MultiSearch, query, page)

    # TODO: Validate
    def title_page_file(self, media_type: str, tmdb_id: int) -> TitlePage:
        """Return TitlePage file."""
        return self._file(TitlePage, media_type, tmdb_id)

    # TODO: Validate
    def movie_search_file(self, query: str, year: int | None = None) -> MovieSearch:
        """Return MovieSearch file."""
        return self._file(MovieSearch, query, year)

    # TODO: Validate
    def tv_search_file(self, query: str, year: int | None = None) -> TvSearch:
        """Return TvSearch file."""
        return self._file(TvSearch, query, year)

    # TODO: Validate
    def movie_detail_file(self, tmdb_id: int) -> MovieDetails:
        """Return MovieDetails file."""
        return self._file(MovieDetails, str(tmdb_id))

    # TODO: Validate
    def show_detail_file(self, tmdb_id: int) -> ShowDetail:
        """Return ShowDetail file."""
        return self._file(ShowDetail, tmdb_id)

    # TODO: Validate
    def changes_since(self, show_key: str) -> date:
        show = Show.get(self.session, self.source, show_key)
        reference = show.update_at if show and show.update_at else tz_datetime.now()
        return (reference - timedelta(days=2)).date()

    # TODO: Validate
    def _latest_show_changes_dates(self) -> dict[int, date | None]:
        cached: dict[int, date | None] = self.session.info.setdefault(
            "tmdb_latest_show_changes_dates",
            {},
        )
        return cached

    # TODO: Validate
    def _latest_show_changes_date(self, tmdb_show_id: int) -> date | None:
        cached = self._latest_show_changes_dates()
        if tmdb_show_id in cached:
            return cached[tmdb_show_id]

        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{ShowChanges.__name__}/{tmdb_show_id}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        stored = self.session.exec(statement).first()
        if stored is None:
            cached[tmdb_show_id] = None
            return None
        identifier = ShowChanges.file_key_to_unique_identifier(stored.key)
        latest = date.fromisoformat(identifier.split("/")[-1])
        cached[tmdb_show_id] = latest
        return latest

    # TODO: Validate
    def show_changes_file(
        self,
        show_key: str,
        downloaded_to: date | None = None,
    ) -> ShowChanges:
        """Return ShowChanges file."""
        _, tmdb_id = parse_show_key(show_key)
        if downloaded_to is None:
            downloaded_to = (
                self._latest_show_changes_date(tmdb_id) or tz_datetime.now().date()
            )
        else:
            self._latest_show_changes_dates().pop(tmdb_id, None)
        return self._file(
            ShowChanges,
            tmdb_id,
            self.changes_since(show_key),
            downloaded_to,
        )

    # TODO: Validate
    def incomplete_show_changes_files(self, show_key: str) -> list[ShowChanges]:
        """Return every ShowChanges file for a title not yet read to the end."""
        _, tmdb_id = parse_show_key(show_key)
        since = self.changes_since(show_key)
        return self.get_incomplete_files(
            ShowChanges,
            lambda stored: self._file(
                ShowChanges,
                tmdb_id,
                since,
                date.fromisoformat(
                    ShowChanges.file_key_to_unique_identifier(stored.key).split("/")[
                        -1
                    ],
                ),
            ),
            key_prefix=f"{tmdb_id}/",
        )

    # TODO: Validate
    def stored_episode_translations_files(
        self,
        tmdb_show_id: int,
    ) -> list[EpisodeTranslations]:
        """Return every EpisodeTranslations file already held for a title."""
        statement = select(File).where(
            File.plugin == self.plugin,
            col(File.key).startswith(
                f"{EpisodeTranslations.__name__}/{tmdb_show_id}/",
            ),
        )
        files: list[EpisodeTranslations] = []
        for stored in self.session.exec(statement).all():
            identifier = EpisodeTranslations.file_key_to_unique_identifier(stored.key)
            _, season_number, episode_number = identifier.split("/")
            files.append(
                self.episode_translations_file(
                    tmdb_show_id,
                    int(season_number),
                    int(episode_number),
                ),
            )
        return files

    # TODO: Validate
    def episode_groups_file(self, tmdb_id: int) -> EpisodeGroups:
        """Return the EpisodeGroups file for a title."""
        return self._file(EpisodeGroups, tmdb_id)

    # TODO: Validate
    def episode_group_detail_file(self, group_id: str) -> EpisodeGroupDetail:
        """Return the EpisodeGroupDetail file for one episode order."""
        return self._file(EpisodeGroupDetail, group_id)

    # TODO: Validate
    def season_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
    ) -> SeasonDetail:
        """Return SeasonDetail file."""
        return self._file(SeasonDetail, tmdb_show_id, season_number)

    # TODO: Validate
    def episode_detail_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> EpisodeDetail:
        """Return EpisodeDetail file."""
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
        """Return EpisodeTranslations file."""
        return self._file(
            EpisodeTranslations,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    # TODO: Validate
    def tv_detail_file(self, tmdb_id: int) -> TvSeriesDetails:
        """Return TvSeriesDetails file."""
        return self._file(TvSeriesDetails, str(tmdb_id))

    # TODO: Validate
    def movie_watch_providers_file(self, tmdb_id: int) -> MovieWatchProviders:
        """Return MovieWatchProviders file."""
        return self._file(MovieWatchProviders, str(tmdb_id))

    # TODO: Validate
    def tv_watch_providers_file(self, tmdb_id: int) -> TvWatchProviders:
        """Return TvWatchProviders file."""
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
        """Return MovieDetails or TvSeriesDetails file."""
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
        """Return MovieWatchProviders or TvWatchProviders file."""
        if media_type == MediaType.movie:
            return self.movie_watch_providers_file(tmdb_id)
        return self.tv_watch_providers_file(tmdb_id)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        groups_file = self.episode_groups_file(tmdb_id)
        groups_file.download_if_outdated()
        return [
            self.show_changes_file(show_key),
            self.show_detail_file(tmdb_id),
            groups_file,
            *(
                self.episode_group_detail_file(option.id)
                for option in self._episode_group_options(tmdb_id)
            ),
        ]

    # TODO: Validate
    def _episode_group_options(
        self,
        tmdb_id: int,
    ) -> Sequence[EpisodeGroupSummary]:
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
    def _chosen_group(self, show_key: str) -> TvEpisodeGroupModel | None:
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
        changes_file = self.show_changes_file(show_key)
        group_id = self._chosen_group_id(show_key)
        if group_id is not None:
            return [changes_file, self.episode_group_detail_file(group_id)]
        return [
            changes_file,
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
