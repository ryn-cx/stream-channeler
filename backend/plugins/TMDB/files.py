# TODO: Validate
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from functools import cache
from typing import (
    Any,
    overload,
    override,
)

from sqlmodel import Session
from tminidb import TMiniDB
from tminidb.exceptions import ResourceNotFoundError, SeasonChangesNotFoundError
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
from tminidb.tv_season.changes import TvSeasonChanges as TvSeasonChangesEndpoint
from tminidb.tv_season.changes.models import TvSeasonChangesModel
from tminidb.tv_season.details import TvSeasonDetails as TvSeasonEndpoint
from tminidb.tv_season.details.models import TvSeasonDetailsModel
from tminidb.tv_season.watch_providers import (
    TvSeasonWatchProviders as TvSeasonWatchProvidersEndpoint,
)
from tminidb.tv_season.watch_providers.models import TvSeasonWatchProvidersModel
from tminidb.tv_series.changes import TvSeriesChanges as TvSeriesChangesEndpoint
from tminidb.tv_series.changes.models import TvSeriesChangesModel
from tminidb.tv_series.details import TvSeriesDetails as TvSeriesEndpoint
from tminidb.tv_series.details.models import TvSeriesDetailsModel
from tminidb.tv_series.episode_groups import (
    TvSeriesEpisodeGroups as TvSeriesEpisodeGroupsEndpoint,
)
from tminidb.tv_series.episode_groups.models import TvSeriesEpisodeGroupsModel
from tminidb.tv_series.images import TvSeriesImages as TvSeriesImagesEndpoint
from tminidb.tv_series.images.models import TvSeriesImagesModel
from tminidb.tv_series.watch_providers import (
    TvSeriesWatchProviders as TvSeriesWatchProvidersEndpoint,
)
from tminidb.tv_series.watch_providers.models import TvSeriesWatchProvidersModel

from app.canonical_media.keys import tmdb_episode_key, tmdb_season_key
from app.config import settings
from app.files.models import File
from app.media.media_type import TMDBMediaType
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB.episode_groups import show_chosen_group_id
from plugins.TMDB.keys import (
    get_media_type_and_tmdb_id,
    parse_episode_key,
    parse_season_key,
)
from plugins.TMDB.utils import SeasonSource, UtilsMixin
from plugins.utils.base_plugin_v3.files import (
    BaseFile,
    EndpointFile,
    IntegerEndpointFile,
)


@cache
def tminidb() -> TMiniDB:
    return TMiniDB(settings.TMDB_API_READ_TOKEN)


class _MoviesDetails(IntegerEndpointFile[MovieDetailsModel]):
    custom_class_key = "Movies/Details"

    @override
    def _endpoint(self) -> MovieEndpoint:
        return tminidb().movie.details

    # Occurs if the user tries to add an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class _MoviesTranslations(IntegerEndpointFile[MovieTranslationsModel]):
    custom_class_key = "Movies/Translations"

    @override
    def _endpoint(self) -> MovieTranslationsEndpoint:
        return tminidb().movie.translations


class _MoviesWatchProviders(EndpointFile[MovieWatchProvidersModel]):
    custom_class_key = "Movies/Watch Providers"

    @override
    def _endpoint(self) -> MovieWatchProvidersEndpoint:
        return tminidb().movie.watch_providers

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_movie_id: int,
        downloaded_at: date,
    ) -> None:
        self.tmdb_movie_id = tmdb_movie_id
        super().__init__(
            session,
            plugin,
            f"{tmdb_movie_id}/{downloaded_at.isoformat()}",
        )

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_movie_id)


class _TVSeriesWatchProviders(EndpointFile[TvSeriesWatchProvidersModel]):
    custom_class_key = "TV Series/Watch Providers"

    @override
    def _endpoint(self) -> TvSeriesWatchProvidersEndpoint:
        return tminidb().tv_series.watch_providers

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        downloaded_at: date,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{downloaded_at.isoformat()}",
        )

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_show_id)


class _TVSeasonsWatchProviders(EndpointFile[TvSeasonWatchProvidersModel]):
    custom_class_key = "TV Seasons/Watch Providers"

    @override
    def _endpoint(self) -> TvSeasonWatchProvidersEndpoint:
        return tminidb().tv_season.watch_providers

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        tmdb_show_id: int,
        season_number: int,
        downloaded_at: date,
    ) -> None:
        self.tmdb_show_id = tmdb_show_id
        self.season_number = season_number
        super().__init__(
            session,
            plugin,
            f"{tmdb_show_id}/{season_number}/{downloaded_at.isoformat()}",
        )

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_show_id, self.season_number)


type ProvidersFile = (
    _MoviesWatchProviders | _TVSeriesWatchProviders | _TVSeasonsWatchProviders
)


class _TVSeriesDetails(IntegerEndpointFile[TvSeriesDetailsModel]):
    custom_class_key = "TV Series/Details"

    @override
    def _endpoint(self) -> TvSeriesEndpoint:
        return tminidb().tv_series.details

    # Occurs if the user tries to add an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class _TVSeriesImages(IntegerEndpointFile[TvSeriesImagesModel]):
    custom_class_key = "TV Series/Images"

    @override
    def _endpoint(self) -> TvSeriesImagesEndpoint:
        return tminidb().tv_series.images

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            int(self.unique_identifier),
            include_image_language="en,null",
        )


class _TVSeriesEpisodeGroups(IntegerEndpointFile[TvSeriesEpisodeGroupsModel]):
    custom_class_key = "TV Series/Episode Groups"

    @override
    def _endpoint(self) -> TvSeriesEpisodeGroupsEndpoint:
        return tminidb().tv_series.episode_groups


class _TVEpisodeGroupsDetails(EndpointFile[TvEpisodeGroupDetailsModel]):
    custom_class_key = "TV Episode Groups/Details"

    @override
    def _endpoint(self) -> TvEpisodeGroupEndpoint:
        return tminidb().tv_episode_group.details


class _TVSeasonsDetails(EndpointFile[TvSeasonDetailsModel]):
    custom_class_key = "TV Seasons/Details"

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

    # Occurs if the user tries to add an invalid URL.
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.tmdb_show_id, self.season_number)

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ResourceNotFoundError)


class _TVEpisodesDetails(EndpointFile[TvEpisodeDetailsModel]):
    custom_class_key = "TV Episodes/Details"

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


class _TVEpisodesTranslations(EndpointFile[TvEpisodeTranslationsModel]):
    custom_class_key = "TV Episodes/Translations"

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


class _TVSeriesChanges(EndpointFile[TvSeriesChangesModel]):
    custom_class_key = "TV Series/Changes"

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


class _TVSeasonsChanges(EndpointFile[TvSeasonChangesModel]):
    custom_class_key = "TV Seasons/Changes"

    @override
    def _endpoint(self) -> TvSeasonChangesEndpoint:
        return tminidb().tv_season.changes

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        season_tmdb_id: int,
        changed_on: date,
    ) -> None:
        self.season_tmdb_id = season_tmdb_id
        self.changed_on = changed_on
        super().__init__(
            session,
            plugin,
            f"{season_tmdb_id}/{changed_on.isoformat()}",
        )

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            self.season_tmdb_id,
            start_date=self.changed_on,
            end_date=self.changed_on,
        )

    @override
    def _next_update_at(self) -> datetime | None:
        # A day that is not over can still take more changes, so the file asks to
        # be read again once it is. A day already over takes no more.
        if self.changed_on < tz_datetime.now().date():
            return None
        return tz_datetime.combine(
            self.changed_on + timedelta(days=1),
            datetime.min.time(),
        )

    # Occurs when TMDB keeps no change log for the season.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeasonChangesNotFoundError)


class _SearchMulti(EndpointFile[SearchMultiModel]):
    custom_class_key = "Search/Multi"

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

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


class _SearchMovie(EndpointFile[SearchMovieModel]):
    custom_class_key = "Search/Movie"

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

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


class _SearchTV(EndpointFile[SearchTvModel]):
    custom_class_key = "Search/TV"

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

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


# TODO: Validate
class FileMixin(UtilsMixin):
    def search_multi_file(self, query: str, page: int = 1) -> _SearchMulti:
        return self._file(_SearchMulti, query, page)

    def search_movie_file(self, query: str, year: int | None = None) -> _SearchMovie:
        return self._file(_SearchMovie, query, year)

    def search_tv_file(self, query: str, year: int | None = None) -> _SearchTV:
        return self._file(_SearchTV, query, year)

    def movies_details_file(self, tmdb_id: int) -> _MoviesDetails:
        return self._file(_MoviesDetails, str(tmdb_id))

    def movies_translations_file(self, tmdb_id: int) -> _MoviesTranslations:
        return self._file(_MoviesTranslations, str(tmdb_id))

    def tv_series_details_file(self, tmdb_id: int) -> _TVSeriesDetails:
        return self._file(_TVSeriesDetails, tmdb_id)

    def latest_tv_series_changes_file(self, show_key: str) -> _TVSeriesChanges:
        """Return the latest TV Series Changes file for a show.

        If the file does not exist an initial one will be created."""
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        latest = self.latest_dated_file_date(_TVSeriesChanges, f"{tmdb_id}/")
        # If the file does not exist an initial file will be downloaded that covers a
        # single day. If the file does exist only the second parameter is used to get it
        # from the database.
        return self._file(_TVSeriesChanges, tmdb_id, latest, latest)

    @overload
    def tv_series_changes_file(
        self,
        show_key: str,
        downloaded_to: date,
    ) -> _TVSeriesChanges: ...
    @overload
    def tv_series_changes_file(self, show_key: File) -> _TVSeriesChanges: ...
    def tv_series_changes_file(
        self,
        show_key: str | File,
        downloaded_to: date | None = None,
    ) -> _TVSeriesChanges:
        if isinstance(show_key, File):
            identifier = _TVSeriesChanges.file_to_unique_identifier(show_key)
            tmdb_id_str, downloaded_to_str = identifier.split("/")
            tmdb_id = int(tmdb_id_str)
            downloaded_to = date.fromisoformat(downloaded_to_str)
        else:
            _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return self._file(
            _TVSeriesChanges,
            tmdb_id,
            self.latest_dated_file_date(_TVSeriesChanges, f"{tmdb_id}/"),
            downloaded_to,
        )

    @overload
    def tv_seasons_changes_file(
        self,
        season_key: str,
        changed_on: date,
    ) -> _TVSeasonsChanges: ...
    @overload
    def tv_seasons_changes_file(self, season_key: File) -> _TVSeasonsChanges: ...
    def tv_seasons_changes_file(
        self,
        season_key: str | File,
        changed_on: date | None = None,
    ) -> _TVSeasonsChanges:
        if isinstance(season_key, File):
            identifier = _TVSeasonsChanges.file_to_unique_identifier(season_key)
            season_tmdb_id_str, changed_on_str = identifier.split("/")
            season_tmdb_id = int(season_tmdb_id_str)
            changed_on = date.fromisoformat(changed_on_str)
        else:
            _, season_tmdb_id = parse_season_key(season_key)
        return self._file(_TVSeasonsChanges, season_tmdb_id, changed_on)

    def incomplete_tv_seasons_changes_files(
        self,
        season_key: str,
    ) -> list[_TVSeasonsChanges]:
        _, season_tmdb_id = parse_season_key(season_key)
        return self.get_incomplete_files(
            _TVSeasonsChanges,
            self.tv_seasons_changes_file,
            key_prefix=f"{season_tmdb_id}/",
        )

    def incomplete_tv_series_changes_files(
        self,
        show_key: str,
    ) -> list[_TVSeriesChanges]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return self.get_incomplete_files(
            _TVSeriesChanges,
            self.tv_series_changes_file,
            key_prefix=f"{tmdb_id}/",
        )

    def tv_series_images_file(self, tmdb_id: int) -> _TVSeriesImages:
        return self._file(_TVSeriesImages, tmdb_id)

    def tv_series_episode_groups_file(self, tmdb_id: int) -> _TVSeriesEpisodeGroups:
        return self._file(_TVSeriesEpisodeGroups, tmdb_id)

    def tv_episode_groups_details_file(self, group_id: str) -> _TVEpisodeGroupsDetails:
        return self._file(_TVEpisodeGroupsDetails, group_id)

    def tv_seasons_details_file(
        self,
        tmdb_show_id: int,
        season_number: int,
    ) -> _TVSeasonsDetails:
        return self._file(_TVSeasonsDetails, tmdb_show_id, season_number)

    def tv_episodes_details_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> _TVEpisodesDetails:
        return self._file(
            _TVEpisodesDetails,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    def tv_episodes_translations_file(
        self,
        tmdb_show_id: int,
        season_number: int,
        episode_number: int,
    ) -> _TVEpisodesTranslations:
        return self._file(
            _TVEpisodesTranslations,
            tmdb_show_id,
            season_number,
            episode_number,
        )

    def latest_movies_watch_providers_file(
        self,
        tmdb_id: int,
    ) -> _MoviesWatchProviders:
        """Return the latest Movies Watch Providers file for a movie.

        If the file does not exist an initial one will be created."""
        return self._file(
            _MoviesWatchProviders,
            tmdb_id,
            self.latest_dated_file_date(_MoviesWatchProviders, f"{tmdb_id}/"),
        )

    def movies_watch_providers_file(
        self,
        tmdb_id: int,
        downloaded_at: date,
    ) -> _MoviesWatchProviders:
        return self._file(_MoviesWatchProviders, tmdb_id, downloaded_at)

    def latest_tv_series_watch_providers_file(
        self,
        tmdb_id: int,
    ) -> _TVSeriesWatchProviders:
        """Return the latest TV Series Watch Providers file for a show.

        If the file does not exist an initial one will be created."""
        # If no file exists yet the date falls back to today, so the file returned is a
        # new one for today. If one does exist the stored file is returned as it is.
        return self._file(
            _TVSeriesWatchProviders,
            tmdb_id,
            self.latest_dated_file_date(_TVSeriesWatchProviders, f"{tmdb_id}/"),
        )

    def tv_series_watch_providers_file(
        self,
        tmdb_id: int,
        downloaded_at: date,
    ) -> _TVSeriesWatchProviders:
        return self._file(_TVSeriesWatchProviders, tmdb_id, downloaded_at)

    def latest_tv_seasons_watch_providers_file(
        self,
        tmdb_id: int,
        season_number: int,
    ) -> _TVSeasonsWatchProviders:
        """Return the latest TV Seasons Watch Providers file for a season.

        If the file does not exist an initial one will be created."""
        # If no file exists yet the date falls back to today, so the file returned is a
        # new one for today. If one does exist the stored file is returned as it is.
        return self._file(
            _TVSeasonsWatchProviders,
            tmdb_id,
            season_number,
            self.latest_dated_file_date(
                _TVSeasonsWatchProviders,
                f"{tmdb_id}/{season_number}/",
            ),
        )

    def tv_seasons_watch_providers_file(
        self,
        tmdb_id: int,
        season_number: int,
        downloaded_at: date,
    ) -> _TVSeasonsWatchProviders:
        return self._file(
            _TVSeasonsWatchProviders,
            tmdb_id,
            season_number,
            downloaded_at,
        )

    def incomplete_tv_series_watch_providers_files(
        self,
        tmdb_id: int,
    ) -> list[_TVSeriesWatchProviders]:
        return self.get_incomplete_files(
            _TVSeriesWatchProviders,
            lambda stored: self._file(
                _TVSeriesWatchProviders,
                tmdb_id,
                self._get_file_date_from_name(_TVSeriesWatchProviders, stored),
            ),
            key_prefix=f"{tmdb_id}/",
        )

    def incomplete_movies_watch_providers_files(
        self,
        tmdb_id: int,
    ) -> list[_MoviesWatchProviders]:
        return self.get_incomplete_files(
            _MoviesWatchProviders,
            lambda stored: self._file(
                _MoviesWatchProviders,
                tmdb_id,
                self._get_file_date_from_name(_MoviesWatchProviders, stored),
            ),
            key_prefix=f"{tmdb_id}/",
        )

    def incomplete_tv_seasons_watch_providers_files(
        self,
        tmdb_id: int,
        season_number: int,
    ) -> list[_TVSeasonsWatchProviders]:
        return self.get_incomplete_files(
            _TVSeasonsWatchProviders,
            lambda stored: self._file(
                _TVSeasonsWatchProviders,
                tmdb_id,
                season_number,
                self._get_file_date_from_name(_TVSeasonsWatchProviders, stored),
            ),
            key_prefix=f"{tmdb_id}/{season_number}/",
        )

    # TODO: Validate
    def media_detail_file(
        self,
        media_type: TMDBMediaType,
        tmdb_id: int,
    ) -> _MoviesDetails | _TVSeriesDetails:
        if media_type == TMDBMediaType.movie:
            return self.movies_details_file(tmdb_id)
        return self.tv_series_details_file(tmdb_id)

    # TODO: Validate
    def watch_providers_file(
        self,
        media_type: TMDBMediaType,
        tmdb_id: int,
    ) -> _MoviesWatchProviders | _TVSeriesWatchProviders:
        if media_type == TMDBMediaType.movie:
            return self.latest_movies_watch_providers_file(tmdb_id)
        return self.latest_tv_series_watch_providers_file(tmdb_id)

    # TODO: Validate
    def series_seasons(
        self,
        show_key: str,
        update_at: datetime | None = None,
    ) -> list[SeasonSource]:
        msg = "This plugin does not have series seasons."
        raise NotImplementedError(msg)

    # TODO: Validate
    def native_season_numbers(self, season_key: str, show_key: str) -> list[int]:
        msg = "This plugin does not have native season numbers."
        raise NotImplementedError(msg)

    # TODO: Validate
    def _native_season_number(self, season_key: str, show_key: str) -> int:
        msg = "This plugin does not have a native season number."
        raise NotImplementedError(msg)


# TODO: Validate
class SeriesFileMixin(FileMixin):
    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [season.key for season in self.series_seasons(show_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]

        wanted = set(season_keys)
        return [
            tmdb_episode_key(TMDBMediaType.tv, episode.id)
            for season in self.series_seasons(show_key)
            if season.key in wanted
            for episode in season.episodes
        ]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        show = Show.get(self.session, self.source, show_key)
        groups_file = self.tv_series_episode_groups_file(tmdb_id)
        groups = groups_file.parsed_or_none()
        options = groups.results if groups else []
        return [
            self.latest_tv_series_changes_file(show_key),
            self.tv_series_details_file(tmdb_id),
            groups_file,
            *(self.tv_episode_groups_details_file(option.id) for option in options),
            self.tv_series_watch_providers_file(tmdb_id, tz_datetime.now().date())
            if self._watch_providers_due(show)
            else self.latest_tv_series_watch_providers_file(tmdb_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        show = Show.get(self.session, self.source, show_key)
        season = Season.get(self.session, show, season_key) if show else None
        due = self._watch_providers_due(season)
        return [
            *self._season_detail_files(season_key, show_key),
            *(
                self.tv_seasons_watch_providers_file(
                    tmdb_id,
                    season_number,
                    tz_datetime.now().date(),
                )
                if due
                else self.latest_tv_seasons_watch_providers_file(
                    tmdb_id,
                    season_number,
                )
                for season_number in self.native_season_numbers(season_key, show_key)
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
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        _, episode_tmdb_id = parse_episode_key(episode_key)
        files: list[BaseFile[Any]] = [
            # Contains all of the episode information except for translations.
            *self._season_detail_files(season_key, show_key),
        ]
        for season in self.series_seasons(show_key):
            if season.key != season_key:
                continue
            for episode in season.episodes:
                if episode.id != episode_tmdb_id:
                    continue
                files.append(
                    self.tv_episodes_translations_file(
                        tmdb_id,
                        episode.native_season_number,
                        episode.native_episode_number,
                    ),
                )
        return files

    # TODO: Validate
    def _season_detail_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        changes_file = self.latest_tv_series_changes_file(show_key)
        group_id = show_chosen_group_id(self.session, self.source, show_key)
        if group_id is not None:
            return [changes_file, self.tv_episode_groups_details_file(group_id)]
        return [
            changes_file,
            self.tv_seasons_details_file(
                tmdb_id,
                self._native_season_number(season_key, show_key),
            ),
        ]


# TODO: Validate
class MovieFileMixin(FileMixin):
    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        media_type, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [tmdb_season_key(media_type, tmdb_id)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        media_type, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [tmdb_episode_key(media_type, tmdb_id)]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        show = Show.get(self.session, self.source, show_key)
        return [
            self.movies_details_file(tmdb_id),
            self.movies_watch_providers_file(tmdb_id, tz_datetime.now().date())
            if self._watch_providers_due(show)
            else self.latest_movies_watch_providers_file(tmdb_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [self.movies_details_file(tmdb_id)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        return [self.movies_details_file(tmdb_id)]
