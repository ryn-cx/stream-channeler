# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, Literal, overload, override

from chirashi import Chirashi
from chirashi.browse_series import models as browse_series_models
from chirashi.objects import models as objects_models
from chirashi.search import models as search_models
from chirashi.season_episodes import models as episodes_models
from chirashi.seasons import models as seasons_models
from chirashi.series import models as series_models

from app.files.models import File
from app.utils import tz_datetime
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, GAPIListJSON
from plugins.utils.get_around_client import get_around_client


@cache
def chirashi() -> Chirashi:
    return Chirashi(get_around_client=get_around_client())


class Series(GAPIJSON[series_models.SeriesModel]):
    # Occurs when a user puts in an invalid series URL.
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"
    API_ENDPOINT = chirashi().series

    def acceptable_error_extra_value(self) -> str:
        return f"Invalid series_id {self.unique_identifier}"


class Objects(GAPIJSON[objects_models.ObjectsModel]):
    # Occurs when a user puts in an invalid episode URL.
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

    def extract_datums(self) -> list[browse_series_models.Datum]:
        return chirashi().browse_series.compile_entries(self.parsed())


class Search(GAPIJSON[search_models.SearchModel]):
    API_ENDPOINT = chirashi().search


class FileMixin(TMDBMixin, register=False):
    def series_file(self, show_key: str) -> Series:
        return self._get_cached_file(
            Series,
            show_key,
            lambda: Series(self.session, self.plugin, show_key),
        )

    def objects_file(self, episode_key: str) -> Objects:
        return self._get_cached_file(
            Objects,
            episode_key,
            lambda: Objects(self.session, self.plugin, episode_key),
        )

    def seasons_file(self, show_key: str) -> Seasons:
        return self._get_cached_file(
            Seasons,
            show_key,
            lambda: Seasons(self.session, self.plugin, show_key),
        )

    def episodes_file(self, season_key: str) -> SeasonEpisodes:
        return self._get_cached_file(
            SeasonEpisodes,
            season_key,
            lambda: SeasonEpisodes(self.session, self.plugin, season_key),
        )

    def browse_file(self, browse_datetime: datetime | File) -> BrowseSeries:
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
        return self._get_cached_file(
            Search,
            query,
            lambda: Search(self.session, self.plugin, query),
        )

    @override
    def _source_files(self) -> Sequence[BrowseSeries]:
        if file := self.get_newest_browse_file(is_completed=True):
            return [file]
        return []

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file(
            [
                # Required to detect new seasons.
                self.seasons_file(show_key),
                # Required to detect changes to the show.
                self.series_file(show_key),
            ],
            show_key,
        )

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_season_file(
            [
                # Required to detect new episodes.
                self.episodes_file(season_key),
                # Required to detect changes to the season.
                self.seasons_file(show_key),
            ],
            season_key,
            show_key,
        )

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_episode_file(
            [self.episodes_file(season_key)],
            episode_key,
            season_key,
            show_key,
        )

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

    @overload
    def get_newest_browse_file(
        self,
        *,
        is_completed: bool = ...,
        strict: Literal[True],
    ) -> BrowseSeries: ...

    @overload
    def get_newest_browse_file(
        self,
        *,
        is_completed: bool = ...,
        strict: Literal[False] = ...,
    ) -> BrowseSeries | None: ...

    def get_newest_browse_file(
        self,
        *,
        is_completed: bool = False,
        strict: bool = False,
    ) -> BrowseSeries | None:
        extra = "Completed" if is_completed else None
        if file := self.preload_latest_file(BrowseSeries, extra=extra):
            return self.browse_file(file)

        if strict:
            msg = "No browse file found."
            raise FileNotFoundError(msg)
        return None
