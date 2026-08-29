# TODO: Validate
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from functools import cache
from typing import (
    Any,
    Literal,
    overload,
    override,
)

from sqlmodel import Session, col, select
from tminidb import TMiniDB
from tminidb.exceptions import ResourceNotFoundError
from tminidb.movie.details import MovieDetails as MovieEndpoint
from tminidb.movie.details.models import MovieDetailsModel
from tminidb.movie.translations import (
    MovieTranslations as MovieTranslationsEndpoint,
)
from tminidb.movie.translations.models import MovieTranslationsModel
from tminidb.movie.watch_providers import (
    MovieWatchProviders as MovieWatchProvidersEndpoint,
)
from tminidb.movie.watch_providers.models import MovieWatchProvidersModel
from tminidb.search.movie import SearchMovie as SearchMovieEndpoint
from tminidb.search.movie.models import SearchMovieModel
from tminidb.search.multi import SearchMulti as SearchMultiEndpoint
from tminidb.search.multi.models import SearchMultiModel
from tminidb.search.tv import SearchTv as SearchTvEndpoint
from tminidb.search.tv.models import SearchTvModel
from tminidb.tv_episode.details import TvEpisodeDetails as TvEpisodeEndpoint
from tminidb.tv_episode.details.models import TvEpisodeDetailsModel
from tminidb.tv_episode.translations import (
    TvEpisodeTranslations as TvEpisodeTranslationsEndpoint,
)
from tminidb.tv_episode.translations.models import TvEpisodeTranslationsModel
from tminidb.tv_episode_group.details import (
    TvEpisodeGroupDetails as TvEpisodeGroupEndpoint,
)
from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel
from tminidb.tv_season.details import TvSeasonDetails as TvSeasonEndpoint
from tminidb.tv_season.details.models import TvSeasonDetailsModel
from tminidb.tv_series.changes import TvSeriesChanges as TvSeriesChangesEndpoint
from tminidb.tv_series.changes.models import TvSeriesChangesModel
from tminidb.tv_series.details import TvSeriesDetails as TvSeriesEndpoint
from tminidb.tv_series.details.models import TvSeriesDetailsModel
from tminidb.tv_series.episode_groups import (
    TvSeriesEpisodeGroups as TvSeriesEpisodeGroupsEndpoint,
)
from tminidb.tv_series.episode_groups.models import TvSeriesEpisodeGroupsModel
from tminidb.tv_series.watch_providers import (
    TvSeriesWatchProviders as TvSeriesWatchProvidersEndpoint,
)
from tminidb.tv_series.watch_providers.models import TvSeriesWatchProvidersModel

from app.config import settings
from app.files.models import File
from app.media.media_type import MediaType
from app.plugins.models import Plugin
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB.constants import media_url
from plugins.TMDB.episode_groups import show_chosen_group_id
from plugins.TMDB.keys import (
    parse_season_key,
    parse_show_key,
)
from plugins.utils.base_plugin.files import (
    BaseFile,
    EndpointFile,
    HTMLFile,
    IntegerEndpointFile,
)
from plugins.utils.base_plugin.plugin import BasePlugin


@cache
def tminidb() -> TMiniDB:
    return TMiniDB(settings.TMDB_API_READ_TOKEN)


class MovieDetails(IntegerEndpointFile[MovieDetailsModel]):
    @override
    def _endpoint(self) -> MovieEndpoint:
        return tminidb().movie.details

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class MovieTranslations(IntegerEndpointFile[MovieTranslationsModel]):
    @override
    def _endpoint(self) -> MovieTranslationsEndpoint:
        return tminidb().movie.translations

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class TvSeriesDetails(IntegerEndpointFile[TvSeriesDetailsModel]):
    @override
    def _endpoint(self) -> TvSeriesEndpoint:
        return tminidb().tv_series.details

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class MovieWatchProviders(IntegerEndpointFile[MovieWatchProvidersModel]):
    @override
    def _endpoint(self) -> MovieWatchProvidersEndpoint:
        return tminidb().movie.watch_providers


class TvWatchProviders(IntegerEndpointFile[TvSeriesWatchProvidersModel]):
    @override
    def _endpoint(self) -> TvSeriesWatchProvidersEndpoint:
        return tminidb().tv_series.watch_providers


class ShowDetail(IntegerEndpointFile[TvSeriesDetailsModel]):
    @override
    def _endpoint(self) -> TvSeriesEndpoint:
        return tminidb().tv_series.details

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class EpisodeGroups(IntegerEndpointFile[TvSeriesEpisodeGroupsModel]):
    @override
    def _endpoint(self) -> TvSeriesEpisodeGroupsEndpoint:
        return tminidb().tv_series.episode_groups

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class EpisodeGroupDetail(EndpointFile[TvEpisodeGroupDetailsModel]):
    @override
    def _endpoint(self) -> TvEpisodeGroupEndpoint:
        return tminidb().tv_episode_group.details

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


# TODO: Validate
class SeasonDetail(EndpointFile[TvSeasonDetailsModel]):
    @override
    def _endpoint(self) -> TvSeasonEndpoint:
        return tminidb().tv_season.details

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

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_show_id, self.season_number)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class EpisodeDetail(EndpointFile[TvEpisodeDetailsModel]):
    @override
    def _endpoint(self) -> TvEpisodeEndpoint:
        return tminidb().tv_episode.details

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

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )


# TODO: Validate
class EpisodeTranslations(EndpointFile[TvEpisodeTranslationsModel]):
    @override
    def _endpoint(self) -> TvEpisodeTranslationsEndpoint:
        return tminidb().tv_episode.translations

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

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            self.tmdb_show_id,
            self.season_number,
            self.episode_number,
        )

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class ShowChanges(EndpointFile[TvSeriesChangesModel]):
    @override
    def _endpoint(self) -> TvSeriesChangesEndpoint:
        return tminidb().tv_series.changes

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

    @override
    def _download_file(self) -> str:
        return self._endpoint().download_merged(
            self.tmdb_show_id,
            self.since,
            tz_datetime.now().date(),
        )


class MultiSearch(EndpointFile[SearchMultiModel]):
    @override
    def _endpoint(self) -> SearchMultiEndpoint:
        return tminidb().search.multi

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        query: str,
        page: int = 1,
    ) -> None:
        self.query = query
        self.page = page
        super().__init__(session, plugin, f"{query}/{page}")

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, page=self.page)

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


class TitlePage(HTMLFile):
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

    @override
    def _url(self) -> str:
        return media_url(self.media_type, self.tmdb_id)


class MovieSearch(EndpointFile[SearchMovieModel]):
    @override
    def _endpoint(self) -> SearchMovieEndpoint:
        return tminidb().search.movie

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

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, year=self.year)

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


class TvSearch(EndpointFile[SearchTvModel]):
    @override
    def _endpoint(self) -> SearchTvEndpoint:
        return tminidb().search.tv

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

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.query, year=self.year)

    # TODO: Validate

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


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
    def movie_translations_file(self, tmdb_id: int) -> MovieTranslations:
        """Return MovieTranslations file."""
        return self._file(MovieTranslations, str(tmdb_id))

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
        options = (
            groups_file.parsed().results if groups_file.database_record.content else []
        )
        return [
            self.show_changes_file(show_key),
            self.show_detail_file(tmdb_id),
            groups_file,
            *(self.episode_group_detail_file(option.id) for option in options),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        changes_file = self.show_changes_file(show_key)
        group_id = show_chosen_group_id(self.session, self.source, show_key)
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
