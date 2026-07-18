"""Crunchyroll plugin files."""

from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import override

from chirashi import Chirashi
from chirashi.browse_series import models as browse_series_models
from chirashi.objects import models as objects_models
from chirashi.search import models as search_models
from chirashi.season_episodes import models as episodes_models
from chirashi.seasons import models as seasons_models
from chirashi.series import models as series_models
from sqlmodel import col, select

from app.files.models import File
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import GAPIJSON, GAPIListJSON
from plugins.utils.get_around_client import get_around_client


@cache
def chirashi() -> Chirashi:
    return Chirashi(get_around_client=get_around_client())


class Series(GAPIJSON[series_models.SeriesModel]):
    # Occurs when a user puts in an invalid URL.
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"
    API_ENDPOINT = chirashi().series

    def acceptable_error_extra_value(self) -> str:
        return f"Invalid series_id {self.unique_identifier}"


class Objects(GAPIJSON[objects_models.ObjectsModel]):
    # Occurs when a user puts in an invalid URL.
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"
    API_ENDPOINT = chirashi().objects

    def acceptable_error_extra_value(self) -> str:
        return f"Invalid episode_id {self.unique_identifier}"


class Seasons(GAPIJSON[seasons_models.SeasonsModel]):
    API_ENDPOINT = chirashi().seasons


class SeasonEpisodes(GAPIJSON[episodes_models.SeasonEpisodesModel]):
    API_ENDPOINT = chirashi().season_episodes


class BrowseSeries(GAPIListJSON[browse_series_models.BrowseSeriesModel]):
    IMMUTABLE = True
    API_ENDPOINT = chirashi().browse_series

    # Need to use download_and_parse_since_datetime instead of download_and_parse so the
    # new BrowseSeriesModel includes entries up to the previous BrowseSeriesModel.
    @override
    def _get(self) -> list[browse_series_models.BrowseSeriesModel]:
        return chirashi().browse_series.download_and_parse_since_datetime(
            end_datetime=tz_datetime.fromisoformat(self.unique_identifier),
        )

    def datums(self) -> list[browse_series_models.Datum]:
        """Extract all of the datum entries from BrowseSeries."""
        return chirashi().browse_series.compile_entries(self.parsed())


class Search(GAPIJSON[search_models.SearchModel]):
    API_ENDPOINT = chirashi().search


class FileMixin(BasePlugin, register=False):
    def series_file(self, show_key: str) -> Series:
        """Return a cached Series for the given show key."""
        return self._get_cached_file(
            Series,
            show_key,
            lambda: Series(self.session, self.plugin, show_key),
        )

    def objects_file(self, episode_key: str) -> Objects:
        """Return a cached Objects file for the given episode key."""
        return self._get_cached_file(
            Objects,
            episode_key,
            lambda: Objects(self.session, self.plugin, episode_key),
        )

    def seasons_file(self, show_key: str) -> Seasons:
        """Return a cached Seasons file the given show key."""
        return self._get_cached_file(
            Seasons,
            show_key,
            lambda: Seasons(self.session, self.plugin, show_key),
        )

    def episodes_file(self, season_key: str) -> SeasonEpisodes:
        """Return a cached Episodes file for the given season key."""
        return self._get_cached_file(
            SeasonEpisodes,
            season_key,
            lambda: SeasonEpisodes(self.session, self.plugin, season_key),
        )

    def browse_file(self, browse_datetime: datetime | File) -> BrowseSeries:
        """Return a cached Browse file for the given datetime or existing File."""
        if isinstance(browse_datetime, File):
            str_datetime = BrowseSeries.file_key_to_unique_identifier(
                browse_datetime.key,
            )
        else:
            str_datetime = str(browse_datetime)
        return self._get_cached_file(
            BrowseSeries,
            str_datetime,
            lambda: BrowseSeries(self.session, self.plugin, str_datetime),
        )

    def search_file(self, query: str) -> Search:
        """Return a cached Search file for the given query."""
        return self._get_cached_file(
            Search,
            query,
            lambda: Search(self.session, self.plugin, query),
        )

    @override
    def _source_files(self, source_key: str) -> Sequence[BrowseSeries]:
        return [self.get_latest_browse_file(is_completed=True)]

    @override
    def _show_files(self, show_key: str) -> Sequence[Series | Seasons]:
        return [
            # Required to detect new seasons.
            self.seasons_file(show_key),
            # Required to detect changes to the show.
            self.series_file(show_key),
        ]

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[Seasons | SeasonEpisodes]:
        return [
            # Required to detect new episodes.
            self.episodes_file(season_key),
            # Required to detect changes to the season.
            self.seasons_file(show_key),
        ]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[SeasonEpisodes]:
        return [self.episodes_file(season_key)]

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        return [
            season_data.id for season_data in self.seasons_file(show_key).parsed().data
        ]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            episode.id
            for season_key in season_keys
            for episode in self.episodes_file(season_key).parsed().data
        ]

    def preload_latest_browse_file(self, *, is_completed: bool = False) -> File | None:
        """Return the most recent browse File from the database, or None.

        Args:
            is_completed: If True, only completed browse files are preloaded.
        """
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{BrowseSeries.__name__}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        if is_completed:
            statement = statement.where(col(File.extra) == "Completed")
        return self.session.exec(statement).first()

    def get_latest_browse_file(self, *, is_completed: bool = False) -> BrowseSeries:
        """Return the latest browse file, downloading one if none exist.

        Args:
            is_completed: If True, only completed browse files are returned.
        """
        if file := self.preload_latest_browse_file(is_completed=is_completed):
            return self.browse_file(file)
        browse = self.browse_file(tz_datetime.now())
        browse.download_if_outdated()

        if is_completed:
            browse.database_record.extra = "Completed"
        return browse
