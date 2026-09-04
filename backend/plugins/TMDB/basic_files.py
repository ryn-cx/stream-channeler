from __future__ import annotations

from datetime import date
from typing import overload

from app.files.models import File
from app.utils import tz_datetime
from plugins.TMDB.files import (
    MoviesDetails,
    MoviesTranslations,
    MoviesWatchProviders,
    SearchMovie,
    SearchMulti,
    SearchTV,
    TVEpisodeGroupsDetails,
    TVEpisodesTranslations,
    TVSeasonsChanges,
    TVSeasonsDetails,
    TVSeasonsWatchProviders,
    TVSeriesChanges,
    TVSeriesDetails,
    TVSeriesEpisodeGroups,
    TVSeriesImages,
    TVSeriesWatchProviders,
)
from plugins.utils.base_plugin_v3.base import BasePlugin


class BasicFiles(BasePlugin):
    def search_multi_file(self, query: str, page: int = 1) -> SearchMulti:
        return self._file(SearchMulti, query, page)

    def search_movie_file(self, query: str, year: int | None = None) -> SearchMovie:
        return self._file(SearchMovie, query, year)

    def search_tv_file(self, query: str, year: int | None = None) -> SearchTV:
        return self._file(SearchTV, query, year)

    def movies_details_file(self, tmdb_movie_key: int) -> MoviesDetails:
        return self._file(MoviesDetails, str(tmdb_movie_key))

    def movies_translations_file(self, tmdb_movie_key: int) -> MoviesTranslations:
        return self._file(MoviesTranslations, str(tmdb_movie_key))

    def tv_series_details_file(self, tmdb_tv_show_key: int) -> TVSeriesDetails:
        return self._file(TVSeriesDetails, tmdb_tv_show_key)

    def tv_series_images_file(self, tmdb_tv_show_key: int) -> TVSeriesImages:
        return self._file(TVSeriesImages, tmdb_tv_show_key)

    def tv_series_episode_groups_file(
        self,
        tmdb_tv_show_key: int,
    ) -> TVSeriesEpisodeGroups:
        return self._file(TVSeriesEpisodeGroups, tmdb_tv_show_key)

    def tv_episode_groups_details_file(self, group_id: str) -> TVEpisodeGroupsDetails:
        return self._file(TVEpisodeGroupsDetails, group_id)

    def tv_seasons_details_file(
        self,
        tmdb_tv_show_key: int,
        season_number: int,
    ) -> TVSeasonsDetails:
        return self._file(TVSeasonsDetails, tmdb_tv_show_key, season_number)

    def tv_episodes_translations_file(
        self,
        tmdb_tv_show_key: int,
        season_number: int,
        episode_number: int,
    ) -> TVEpisodesTranslations:
        return self._file(
            TVEpisodesTranslations,
            tmdb_tv_show_key,
            season_number,
            episode_number,
        )

    @overload
    def tv_series_changes_file(
        self,
        tmdb_tv_show_key: int,
        downloaded_to: date,
    ) -> TVSeriesChanges: ...
    @overload
    def tv_series_changes_file(self, tmdb_tv_show_key: File) -> TVSeriesChanges: ...
    def tv_series_changes_file(
        self,
        tmdb_tv_show_key: int | File,
        downloaded_to: date | None = None,
    ) -> TVSeriesChanges:
        if isinstance(tmdb_tv_show_key, File):
            identifier = TVSeriesChanges.file_to_unique_identifier(tmdb_tv_show_key)
            tmdb_id_str, downloaded_to_str = identifier.split("/")
            tmdb_tv_show_key = int(tmdb_id_str)
            downloaded_to = date.fromisoformat(downloaded_to_str)
        return self._file(
            TVSeriesChanges,
            tmdb_tv_show_key,
            self.latest_file_date(TVSeriesChanges, f"{tmdb_tv_show_key}/"),
            downloaded_to,
        )

    @overload
    def tv_seasons_changes_file(
        self,
        tmdb_tv_season_key: int,
        changed_on: date,
    ) -> TVSeasonsChanges: ...
    @overload
    def tv_seasons_changes_file(self, tmdb_tv_season_key: File) -> TVSeasonsChanges: ...
    def tv_seasons_changes_file(
        self,
        tmdb_tv_season_key: int | File,
        changed_on: date | None = None,
    ) -> TVSeasonsChanges:
        if isinstance(tmdb_tv_season_key, File):
            identifier = TVSeasonsChanges.file_to_unique_identifier(tmdb_tv_season_key)
            season_tmdb_id_str, changed_on_str = identifier.split("/")
            tmdb_tv_season_key = int(season_tmdb_id_str)
            changed_on = date.fromisoformat(changed_on_str)
        return self._file(TVSeasonsChanges, tmdb_tv_season_key, changed_on)

    def incomplete_tv_seasons_changes_files(
        self,
        tmdb_tv_season_key: int,
    ) -> list[TVSeasonsChanges]:
        return self.get_incomplete_files(
            file_class=TVSeasonsChanges,
            factory=self.tv_seasons_changes_file,
            key_prefix=f"{tmdb_tv_season_key}/",
        )

    def incomplete_tv_series_changes_files(
        self,
        tmdb_tv_show_key: int,
    ) -> list[TVSeriesChanges]:
        return self.get_incomplete_files(
            file_class=TVSeriesChanges,
            factory=self.tv_series_changes_file,
            key_prefix=f"{tmdb_tv_show_key}/",
        )

    def latest_tv_series_changes_file(self, tmdb_tv_show_key: int) -> TVSeriesChanges:
        """Return the latest TV Series Changes file for a show.

        If the file does not exist an initial one will be created."""
        existing_file = self.latest_file_record(TVSeriesChanges, f"{tmdb_tv_show_key}/")
        # If the file does not exist an initial file will be downloaded that covers a
        # single day. If the file does exist only the second parameter is used to get it
        # from the database.
        return self._file(
            TVSeriesChanges, tmdb_tv_show_key, existing_file, existing_file
        )

    @overload
    def movies_watch_providers_file(
        self,
        tmdb_movie_key: int,
        downloaded_at: date,
    ) -> MoviesWatchProviders: ...
    @overload
    def movies_watch_providers_file(
        self,
        tmdb_movie_key: File,
    ) -> MoviesWatchProviders: ...
    def movies_watch_providers_file(
        self,
        tmdb_movie_key: int | File,
        downloaded_at: date | None = None,
    ) -> MoviesWatchProviders:
        if isinstance(tmdb_movie_key, File):
            identifier = MoviesWatchProviders.file_to_unique_identifier(tmdb_movie_key)
            tmdb_id_str, downloaded_at_str = identifier.split("/")
            tmdb_movie_key = int(tmdb_id_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(MoviesWatchProviders, tmdb_movie_key, downloaded_at)

    def latest_movies_watch_providers_file(
        self,
        tmdb_movie_key: int,
    ) -> MoviesWatchProviders:
        """Return the MoviesWatchProviders file.

        If the file does not exist an initial one will be created."""
        existing_file = self.latest_file_record(
            MoviesWatchProviders,
            f"{tmdb_movie_key}/",
        )
        if not existing_file:
            return self.movies_watch_providers_file(
                tmdb_movie_key,
                tz_datetime.now().date(),
            )
        return self.movies_watch_providers_file(existing_file)

    def latest_tv_series_watch_providers_file(
        self,
        tmdb_tv_show_key: int,
    ) -> TVSeriesWatchProviders:
        """Return the TVSeriesWatchProviders file.

        If the file does not exist an initial one will be created."""
        existing_file = self.latest_file_record(
            TVSeriesWatchProviders, f"{tmdb_tv_show_key}/"
        )
        if not existing_file:
            return self.tv_series_watch_providers_file(
                tmdb_tv_show_key=tmdb_tv_show_key,
                downloaded_at=tz_datetime.now().date(),
            )
        return self.tv_series_watch_providers_file(existing_file)

    @overload
    def tv_series_watch_providers_file(
        self,
        tmdb_tv_show_key: int,
        downloaded_at: date,
    ) -> TVSeriesWatchProviders: ...
    @overload
    def tv_series_watch_providers_file(
        self,
        tmdb_tv_show_key: File,
    ) -> TVSeriesWatchProviders: ...
    def tv_series_watch_providers_file(
        self,
        tmdb_tv_show_key: int | File,
        downloaded_at: date | None = None,
    ) -> TVSeriesWatchProviders:
        if isinstance(tmdb_tv_show_key, File):
            identifier = TVSeriesWatchProviders.file_to_unique_identifier(
                tmdb_tv_show_key,
            )
            tmdb_id_str, downloaded_at_str = identifier.split("/")
            tmdb_tv_show_key = int(tmdb_id_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(TVSeriesWatchProviders, tmdb_tv_show_key, downloaded_at)

    def latest_tv_seasons_watch_providers_file(
        self,
        tmdb_tv_show_key: int,
        season_number: int,
    ) -> TVSeasonsWatchProviders:
        """Return the latest TVSeasonsWatchProviders file.

        If the file does not exist an initial one will be created."""
        stored = self.latest_file_record(
            file_class=TVSeasonsWatchProviders,
            file_prefix=f"{tmdb_tv_show_key}/{season_number}/",
        )
        if stored is None:
            return self.tv_seasons_watch_providers_file(
                tmdb_tv_show_key=tmdb_tv_show_key,
                season_number=season_number,
                downloaded_at=tz_datetime.now().date(),
            )
        return self.tv_seasons_watch_providers_file(stored)

    @overload
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_show_key: int,
        season_number: int,
        downloaded_at: date,
    ) -> TVSeasonsWatchProviders: ...
    @overload
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_show_key: File,
    ) -> TVSeasonsWatchProviders: ...
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_show_key: int | File,
        season_number: int | None = None,
        downloaded_at: date | None = None,
    ) -> TVSeasonsWatchProviders:
        if isinstance(tmdb_tv_show_key, File):
            identifier = TVSeasonsWatchProviders.file_to_unique_identifier(
                tmdb_tv_show_key,
            )
            tmdb_id_str, season_number_str, downloaded_at_str = identifier.split("/")
            tmdb_tv_show_key = int(tmdb_id_str)
            season_number = int(season_number_str)
            downloaded_at = date.fromisoformat(downloaded_at_str)
        return self._file(
            TVSeasonsWatchProviders,
            tmdb_tv_show_key,
            season_number,
            downloaded_at,
        )

    def incomplete_tv_series_watch_providers_files(
        self,
        tmdb_tv_show_key: int,
    ) -> list[TVSeriesWatchProviders]:
        return self.get_incomplete_files(
            file_class=TVSeriesWatchProviders,
            factory=self.tv_series_watch_providers_file,
            key_prefix=f"{tmdb_tv_show_key}/",
        )

    def incomplete_movies_watch_providers_files(
        self,
        tmdb_movie_key: int,
    ) -> list[MoviesWatchProviders]:
        return self.get_incomplete_files(
            file_class=MoviesWatchProviders,
            factory=self.movies_watch_providers_file,
            key_prefix=f"{tmdb_movie_key}/",
        )

    def incomplete_tv_seasons_watch_providers_files(
        self,
        tmdb_tv_show_key: int,
        season_number: int,
    ) -> list[TVSeasonsWatchProviders]:
        return self.get_incomplete_files(
            file_class=TVSeasonsWatchProviders,
            factory=self.tv_seasons_watch_providers_file,
            key_prefix=f"{tmdb_tv_show_key}/{season_number}/",
        )
