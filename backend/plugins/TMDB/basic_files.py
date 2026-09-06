# TODO: Validate
from __future__ import annotations

from datetime import date
from typing import overload

from app.files.models import File
from app.utils import tz_datetime
from plugins.TMDB.files import (
    MoviesDetails,
    MoviesWatchProviders,
    SearchMovie,
    SearchMulti,
    SearchTV,
    TVEpisodeGroupsDetails,
    TVSeasonsChanges,
    TVSeasonsDetails,
    TVSeasonsWatchProviders,
    TVSeriesChanges,
    TVSeriesDetails,
    TVSeriesEpisodeGroups,
    TVSeriesImages,
    TVSeriesWatchProviders,
)
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def search_multi_file(self, query: str, page: int = 1) -> SearchMulti:
        return self._file(SearchMulti, query, page)

    # TODO: Validate
    def search_movie_file(self, query: str, year: int | None = None) -> SearchMovie:
        return self._file(SearchMovie, query, year)

    # TODO: Validate
    def search_tv_file(self, query: str, year: int | None = None) -> SearchTV:
        return self._file(SearchTV, query, year)

    # TODO: Validate
    def movies_details_file(self, tmdb_movie_id: int) -> MoviesDetails:
        return self._file(MoviesDetails, str(tmdb_movie_id))

    # TODO: Validate
    def tv_series_details_file(self, tmdb_tv_title_id: int) -> TVSeriesDetails:
        return self._file(TVSeriesDetails, tmdb_tv_title_id)

    # TODO: Validate
    def tv_series_images_file(self, tmdb_tv_title_id: int) -> TVSeriesImages:
        return self._file(TVSeriesImages, tmdb_tv_title_id)

    # TODO: Validate
    def tv_series_episode_groups_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesEpisodeGroups:
        return self._file(TVSeriesEpisodeGroups, tmdb_tv_title_id)

    # TODO: Validate
    def tv_episode_groups_details_file(self, group_id: str) -> TVEpisodeGroupsDetails:
        return self._file(TVEpisodeGroupsDetails, group_id)

    # TODO: Validate
    def tv_seasons_details_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsDetails:
        return self._file(TVSeasonsDetails, tmdb_tv_title_id, season_number)

    # TODO: Validate
    @overload
    def tv_series_changes_file(
        self,
        tmdb_tv_title_id: int,
        downloaded_to: date,
    ) -> TVSeriesChanges: ...
    # TODO: Validate
    @overload
    def tv_series_changes_file(self, tmdb_tv_title_id: File) -> TVSeriesChanges: ...
    # TODO: Validate
    def tv_series_changes_file(
        self,
        tmdb_tv_title_id: int | File,
        downloaded_to: date | None = None,
    ) -> TVSeriesChanges:
        if isinstance(tmdb_tv_title_id, File):
            identifier = TVSeriesChanges.file_to_unique_identifier(tmdb_tv_title_id)
            tmdb_id_str, downloaded_to_str = identifier.split("/")
            tmdb_tv_title_id = int(tmdb_id_str)
            downloaded_to = date.fromisoformat(downloaded_to_str)
        return self._file(
            TVSeriesChanges,
            tmdb_tv_title_id,
            self.latest_file_date(TVSeriesChanges, f"{tmdb_tv_title_id}/"),
            downloaded_to,
        )

    # TODO: Validate
    @overload
    def tv_seasons_changes_file(
        self,
        tmdb_tv_season_id: int,
        changed_on: date,
    ) -> TVSeasonsChanges: ...
    # TODO: Validate
    @overload
    def tv_seasons_changes_file(self, tmdb_tv_season_id: File) -> TVSeasonsChanges: ...
    # TODO: Validate
    def tv_seasons_changes_file(
        self,
        tmdb_tv_season_id: int | File,
        changed_on: date | None = None,
    ) -> TVSeasonsChanges:
        if isinstance(tmdb_tv_season_id, File):
            identifier = TVSeasonsChanges.file_to_unique_identifier(tmdb_tv_season_id)
            season_tmdb_id_str, changed_on_str = identifier.split("/")
            tmdb_tv_season_id = int(season_tmdb_id_str)
            changed_on = date.fromisoformat(changed_on_str)
        return self._file(TVSeasonsChanges, tmdb_tv_season_id, changed_on)

    # TODO: Validate
    def incomplete_tv_seasons_changes_files(
        self,
        tmdb_tv_season_id: int,
    ) -> list[TVSeasonsChanges]:
        return self.get_incomplete_files(
            file_class=TVSeasonsChanges,
            factory=self.tv_seasons_changes_file,
            key_prefix=f"{tmdb_tv_season_id}/",
        )

    # TODO: Validate
    def incomplete_tv_series_changes_files(
        self,
        tmdb_tv_title_id: int,
    ) -> list[TVSeriesChanges]:
        return self.get_incomplete_files(
            file_class=TVSeriesChanges,
            factory=self.tv_series_changes_file,
            key_prefix=f"{tmdb_tv_title_id}/",
        )

    # TODO: Validate
    def latest_tv_series_changes_file(self, tmdb_tv_title_id: int) -> TVSeriesChanges:
        """Return the latest TV Series Changes file for a title.

        If the file does not exist an initial one will be created."""
        existing_file = self.latest_file_record(TVSeriesChanges, f"{tmdb_tv_title_id}/")
        # If the file does not exist an initial file will be downloaded that covers a
        # single day. If the file does exist only the second parameter is used to get it
        # from the database.
        if not existing_file:
            return self.tv_series_changes_file(
                tmdb_tv_title_id,
                tz_datetime.now().date(),
            )
        return self.tv_series_changes_file(existing_file)

    # TODO: Validate
    @overload
    def movies_watch_providers_file(
        self,
        tmdb_movie_id: int,
        downloaded_at: date,
    ) -> MoviesWatchProviders: ...
    # TODO: Validate
    @overload
    def movies_watch_providers_file(
        self,
        tmdb_movie_id: File,
    ) -> MoviesWatchProviders: ...
    # TODO: Validate
    def movies_watch_providers_file(
        self,
        tmdb_movie_id: int | File,
        downloaded_at: date | None = None,
    ) -> MoviesWatchProviders:
        if isinstance(tmdb_movie_id, File):
            identifier = MoviesWatchProviders.file_to_unique_identifier(tmdb_movie_id)
            tmdb_id_str, downloaded_at_str = identifier.split("/")
            tmdb_movie_id = int(tmdb_id_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(MoviesWatchProviders, tmdb_movie_id, downloaded_at)

    # TODO: Validate
    def latest_movies_watch_providers_file(
        self,
        tmdb_movie_id: int,
    ) -> MoviesWatchProviders:
        """Return the MoviesWatchProviders file.

        If the file does not exist an initial one will be created."""
        existing_file = self.latest_file_record(
            MoviesWatchProviders,
            f"{tmdb_movie_id}/",
        )
        if not existing_file:
            return self.movies_watch_providers_file(
                tmdb_movie_id,
                tz_datetime.now().date(),
            )
        return self.movies_watch_providers_file(existing_file)

    # TODO: Validate
    def latest_tv_series_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesWatchProviders:
        """Return the TVSeriesWatchProviders file.

        If the file does not exist an initial one will be created."""
        existing_file = self.latest_file_record(
            TVSeriesWatchProviders,
            f"{tmdb_tv_title_id}/",
        )
        if not existing_file:
            return self.tv_series_watch_providers_file(
                tmdb_tv_title_id=tmdb_tv_title_id,
                downloaded_at=tz_datetime.now().date(),
            )
        return self.tv_series_watch_providers_file(existing_file)

    # TODO: Validate
    @overload
    def tv_series_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
        downloaded_at: date,
    ) -> TVSeriesWatchProviders: ...
    # TODO: Validate
    @overload
    def tv_series_watch_providers_file(
        self,
        tmdb_tv_title_id: File,
    ) -> TVSeriesWatchProviders: ...
    # TODO: Validate
    def tv_series_watch_providers_file(
        self,
        tmdb_tv_title_id: int | File,
        downloaded_at: date | None = None,
    ) -> TVSeriesWatchProviders:
        if isinstance(tmdb_tv_title_id, File):
            identifier = TVSeriesWatchProviders.file_to_unique_identifier(
                tmdb_tv_title_id,
            )
            tmdb_id_str, downloaded_at_str = identifier.split("/")
            tmdb_tv_title_id = int(tmdb_id_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(TVSeriesWatchProviders, tmdb_tv_title_id, downloaded_at)

    # TODO: Validate
    def latest_tv_seasons_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsWatchProviders:
        """Return the latest TVSeasonsWatchProviders file.

        If the file does not exist an initial one will be created."""
        stored = self.latest_file_record(
            file_class=TVSeasonsWatchProviders,
            file_prefix=f"{tmdb_tv_title_id}/{season_number}/",
        )
        if stored is None:
            return self.tv_seasons_watch_providers_file(
                tmdb_tv_title_id=tmdb_tv_title_id,
                season_number=season_number,
                downloaded_at=tz_datetime.now().date(),
            )
        return self.tv_seasons_watch_providers_file(stored)

    # TODO: Validate
    @overload
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
        downloaded_at: date,
    ) -> TVSeasonsWatchProviders: ...
    # TODO: Validate
    @overload
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_title_id: File,
    ) -> TVSeasonsWatchProviders: ...
    # TODO: Validate
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_title_id: int | File,
        season_number: int | None = None,
        downloaded_at: date | None = None,
    ) -> TVSeasonsWatchProviders:
        if isinstance(tmdb_tv_title_id, File):
            identifier = TVSeasonsWatchProviders.file_to_unique_identifier(
                tmdb_tv_title_id,
            )
            tmdb_id_str, season_number_str, downloaded_at_str = identifier.split("/")
            tmdb_tv_title_id = int(tmdb_id_str)
            season_number = int(season_number_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(
            TVSeasonsWatchProviders,
            tmdb_tv_title_id,
            season_number,
            downloaded_at,
        )

    # TODO: Validate
    def incomplete_tv_series_watch_providers_files(
        self,
        tmdb_tv_title_id: int,
    ) -> list[TVSeriesWatchProviders]:
        return self.get_incomplete_files(
            file_class=TVSeriesWatchProviders,
            factory=self.tv_series_watch_providers_file,
            key_prefix=f"{tmdb_tv_title_id}/",
        )

    # TODO: Validate
    def incomplete_movies_watch_providers_files(
        self,
        tmdb_movie_id: int,
    ) -> list[MoviesWatchProviders]:
        return self.get_incomplete_files(
            file_class=MoviesWatchProviders,
            factory=self.movies_watch_providers_file,
            key_prefix=f"{tmdb_movie_id}/",
        )

    # TODO: Validate
    def incomplete_tv_seasons_watch_providers_files(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> list[TVSeasonsWatchProviders]:
        return self.get_incomplete_files(
            file_class=TVSeasonsWatchProviders,
            factory=self.tv_seasons_watch_providers_file,
            key_prefix=f"{tmdb_tv_title_id}/{season_number}/",
        )
