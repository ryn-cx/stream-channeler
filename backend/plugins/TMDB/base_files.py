# TODO: Validate
from __future__ import annotations

from datetime import date

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
class TMDBBaseFiles(BasePlugin):
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
    def tv_series_changes_file(
        self,
        tmdb_tv_title_id: int | File,
        downloaded_to: date | None = None,
    ) -> TVSeriesChanges:
        if isinstance(tmdb_tv_title_id, File):
            identifier = TVSeriesChanges.file_to_unique_identifier(tmdb_tv_title_id)
            tmdb_id_str, downloaded_to_str = identifier.split("/")
            return self.tv_series_changes_file(
                int(tmdb_id_str),
                date.fromisoformat(downloaded_to_str),
            )

        existing_record = self.latest_file_record(
            file_class=TVSeriesChanges,
            file_prefix=tmdb_tv_title_id,
        )
        if existing_record:
            since = self._date_from_file_name(TVSeriesChanges, existing_record)
        else:
            since = tz_datetime.now().date()

        return self._cached_file(
            TVSeriesChanges,
            tmdb_tv_title_id,
            since,
            downloaded_to,
        )

    # TODO: Validate
    def tv_seasons_changes_file(
        self,
        tmdb_tv_season_id: int | File,
        changed_on: date | None = None,
    ) -> TVSeasonsChanges:
        if isinstance(tmdb_tv_season_id, File):
            identifier = TVSeasonsChanges.file_to_unique_identifier(tmdb_tv_season_id)
            season_tmdb_id_str, changed_on_str = identifier.split("/")
            return self.tv_seasons_changes_file(
                int(season_tmdb_id_str),
                date.fromisoformat(changed_on_str),
            )

        return self._cached_file(TVSeasonsChanges, tmdb_tv_season_id, changed_on)

    # TODO: Validate
    def incomplete_tv_seasons_changes_files(
        self,
        tmdb_tv_season_id: int,
    ) -> list[TVSeasonsChanges]:
        return self._incomplete_files(
            file_class=TVSeasonsChanges,
            factory=self.tv_seasons_changes_file,
            key_prefix=tmdb_tv_season_id,
        )

    # TODO: Validate
    def incomplete_tv_series_changes_files(
        self,
        tmdb_tv_title_id: int,
    ) -> list[TVSeriesChanges]:
        return self._incomplete_files(
            file_class=TVSeriesChanges,
            factory=self.tv_series_changes_file,
            key_prefix=tmdb_tv_title_id,
        )

    # TODO: Validate
    def _cached_latest_tv_series_changes_files(self) -> dict[int, TVSeriesChanges]:
        cached: dict[int, TVSeriesChanges] = self.session.info.setdefault(
            "tmdb_latest_tv_series_changes_files",
            {},
        )
        return cached

    # TODO: Validate
    def forget_latest_tv_series_changes_file(self, tmdb_tv_title_id: int) -> None:
        self._cached_latest_tv_series_changes_files().pop(tmdb_tv_title_id, None)

    # TODO: Validate
    def get_or_create_latest_tv_series_changes_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesChanges:
        """Return the latest TV Series Changes file for a title.

        If the file does not exist an initial one will be created."""
        cached = self._cached_latest_tv_series_changes_files()
        if tmdb_tv_title_id in cached:
            return cached[tmdb_tv_title_id]

        existing_record = self.latest_file_record(
            file_class=TVSeriesChanges,
            file_prefix=tmdb_tv_title_id,
        )
        changes_file: TVSeriesChanges
        if existing_record:
            changes_file = self.tv_series_changes_file(existing_record)
        else:
            changes_file = self.tv_series_changes_file(
                tmdb_tv_title_id,
                tz_datetime.now().date(),
            )

        cached[tmdb_tv_title_id] = changes_file
        return changes_file

    # TODO: Validate
    def movies_watch_providers_file(
        self,
        tmdb_movie_id: int | File,
        downloaded_at: date | None = None,
    ) -> MoviesWatchProviders:
        if isinstance(tmdb_movie_id, File):
            identifier = MoviesWatchProviders.file_to_unique_identifier(tmdb_movie_id)
            tmdb_id_str, downloaded_at_str = identifier.split("/")
            return self.movies_watch_providers_file(
                int(tmdb_id_str),
                date.fromisoformat(downloaded_at_str),
            )

        return self._cached_file(MoviesWatchProviders, tmdb_movie_id, downloaded_at)

    # TODO: Validate
    def _get_or_create_latest_movies_watch_providers_file(
        self,
        tmdb_movie_id: int,
    ) -> MoviesWatchProviders:
        """Return the MoviesWatchProviders file.

        If the file does not exist an initial one will be created."""
        existing_record = self.latest_file_record(
            file_class=MoviesWatchProviders,
            file_prefix=tmdb_movie_id,
        )
        if existing_record:
            return self.movies_watch_providers_file(existing_record)

        return self.movies_watch_providers_file(
            tmdb_movie_id,
            tz_datetime.now().date(),
        )

    # TODO: Validate
    def _get_or_create_latest_tv_series_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesWatchProviders:
        """Return the TVSeriesWatchProviders file.

        If the file does not exist an initial one will be created."""
        existing_record = self.latest_file_record(
            file_class=TVSeriesWatchProviders,
            file_prefix=tmdb_tv_title_id,
        )
        if existing_record:
            return self.tv_series_watch_providers_file(existing_record)

        return self.tv_series_watch_providers_file(
            tmdb_tv_title_id,
            tz_datetime.now().date(),
        )

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
            return self.tv_series_watch_providers_file(
                int(tmdb_id_str),
                date.fromisoformat(downloaded_at_str),
            )

        return self._cached_file(
            TVSeriesWatchProviders,
            tmdb_tv_title_id,
            downloaded_at,
        )

    # TODO: Validate
    def _get_or_create_latest_tv_seasons_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsWatchProviders:
        """Return the latest TVSeasonsWatchProviders file.

        If the file does not exist an initial one will be created."""
        existing_record = self.latest_file_record(
            file_class=TVSeasonsWatchProviders,
            file_prefix=f"{tmdb_tv_title_id}/{season_number}",
        )
        if existing_record:
            return self.tv_seasons_watch_providers_file(existing_record)

        return self.tv_seasons_watch_providers_file(
            tmdb_tv_title_id,
            season_number,
            tz_datetime.now().date(),
        )

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
            return self.tv_seasons_watch_providers_file(
                int(tmdb_id_str),
                int(season_number_str),
                date.fromisoformat(downloaded_at_str),
            )

        return self._cached_file(
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
        return self._incomplete_files(
            file_class=TVSeriesWatchProviders,
            factory=self.tv_series_watch_providers_file,
            key_prefix=tmdb_tv_title_id,
        )

    # TODO: Validate
    def incomplete_movies_watch_providers_files(
        self,
        tmdb_movie_id: int,
    ) -> list[MoviesWatchProviders]:
        return self._incomplete_files(
            file_class=MoviesWatchProviders,
            factory=self.movies_watch_providers_file,
            key_prefix=tmdb_movie_id,
        )

    # TODO: Validate
    def incomplete_tv_seasons_watch_providers_files(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> list[TVSeasonsWatchProviders]:
        return self._incomplete_files(
            file_class=TVSeasonsWatchProviders,
            factory=self.tv_seasons_watch_providers_file,
            key_prefix=f"{tmdb_tv_title_id}/{season_number}",
        )
