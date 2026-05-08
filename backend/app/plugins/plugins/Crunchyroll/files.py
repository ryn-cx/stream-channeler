# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import override

from chirashi import Chirashi
from chirashi.browse_series import models as browse_series_models
from chirashi.episodes import models as episodes_models
from chirashi.search import models as search_models
from chirashi.seasons import models as seasons_models
from chirashi.series import models as series_models
from sqlmodel import col, select

from app.config import settings
from app.plugins.models import File
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.plugins.plugins.utils.base_plugin.files import GAPIJSON, GAPIListJSON
from app.utils import tz_datetime


@cache
def chirashi() -> Chirashi:
    server: str | None = settings.GET_AROUND_SERVER
    if server == "changethis":
        server = None
    password: str | None = settings.GET_AROUND_PASSWORD
    if password == "changethis":  # noqa: S105
        password = None
    return Chirashi(get_around_server=server, get_around_password=password)


class Series(GAPIJSON[series_models.Series]):
    # Occurs when a user puts in an invalid URL.
    acceptable_error = "Unexpected response status code: 404"
    api_endpoint = chirashi().series


class Seasons(GAPIJSON[seasons_models.Seasons]):
    api_endpoint = chirashi().seasons


class Episodes(GAPIJSON[episodes_models.Episodes]):
    api_endpoint = chirashi().episodes


class Browse(GAPIListJSON[browse_series_models.BrowseSeries]):
    IMMUTABLE = True
    api_endpoint = chirashi().browse_series

    # Uses get_since_datetime instead of get
    @override
    def _get(self) -> list[browse_series_models.BrowseSeries]:
        return chirashi().browse_series.get_since_datetime(
            end_datetime=tz_datetime.fromisoformat(self.unique_identifier),
        )

    def datums(self) -> list[browse_series_models.Datum]:
        """Extract all of the datum entries from the browse files."""
        return chirashi().browse_series.extract_entries(self.parsed())


class Search(GAPIJSON[search_models.Search]):
    api_endpoint = chirashi().search

    # Use alternative search parameters that have more results.
    @override
    def _get(self) -> search_models.Search:
        # Parameters from: https://www.crunchyroll.com/search?f=series&q=Query
        return chirashi().search.get(
            self.unique_identifier,
            n=100,
            type="series",
        )


class FileMixin(BasePlugin, register=False):
    def series_file(self, show_key: str) -> Series:
        """Return a cached series file for the given show key."""
        return self._get_cached_file(
            Series,
            show_key,
            lambda: Series(self.session, self.plugin, show_key),
        )

    def seasons_file(self, show_key: str) -> Seasons:
        """Return a cached seasons file for the given show key."""
        return self._get_cached_file(
            Seasons,
            show_key,
            lambda: Seasons(self.session, self.plugin, show_key),
        )

    def episodes_file(self, season_key: str) -> Episodes:
        """Return a cached episodes file for the given season key."""
        return self._get_cached_file(
            Episodes,
            season_key,
            lambda: Episodes(self.session, self.plugin, season_key),
        )

    def browse_file(self, browse_datetime: datetime | File) -> Browse:
        """Return a cached browse file for the given datetime or existing File."""
        if isinstance(browse_datetime, File):
            str_datetime = Browse.file_key_to_unique_identifier(browse_datetime.key)
        else:
            str_datetime = str(browse_datetime)
        return self._get_cached_file(
            Browse,
            str_datetime,
            lambda: Browse(self.session, self.plugin, str_datetime),
        )

    def search_file(self, query: str) -> Search:
        """Return a cached search file for the given query."""
        return self._get_cached_file(
            Search,
            query,
            lambda: Search(self.session, self.plugin, query),
        )

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
    ) -> Sequence[Seasons | Episodes]:
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
    ) -> Sequence[Episodes]:
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

    def preload_latest_browse_file(self) -> File | None:
        """Return the most recent browse File from the database, or None."""
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{Browse.__name__}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        return self.session.exec(statement).first()

    def get_latest_browse_file(self) -> Browse:
        """Return the latest browse file, downloading a fresh one if none exist."""
        if file := self.preload_latest_browse_file():
            return self.browse_file(file)
        browse = self.browse_file(tz_datetime.now())
        browse.download_if_outdated()
        return browse
