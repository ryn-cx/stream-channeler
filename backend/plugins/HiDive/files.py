# TODO: Validate
"""The files a HiDive title is read out of."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, override

from diving_board import DivingBoard
from diving_board.schedule import models as schedule_models
from diving_board.search import models as search_models
from diving_board.season import models as season_models
from diving_board.series import models as series_models
from diving_board.vod import models as vod_models

from app.files.models import File
from app.utils import tz_datetime
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import (
    GAPIJSON,
    BaseFile,
    GAPIListJSON,
    PartialGAPIJSON,
)
from plugins.utils.base_plugin.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def diving_board() -> DivingBoard:
    """Return a cached Diving Board client."""
    return DivingBoard(get_around_client=get_around_client())


# TODO: Validate
class Season(PartialGAPIJSON[season_models.SeasonModel]):
    """Season file."""

    # Occurs when the user imports an invalid TV show url.
    # TODO: Validate
    @override
    def _get_ACCEPTABLE_ERROR(self) -> str | None:
        return "Unexpected response status code: 404"
    API_ENDPOINT = diving_board().season

    # TODO: Validate
    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _fetch(self) -> season_models.SeasonModel:
        return diving_board().season.download_and_parse(int(self.unique_identifier))


# TODO: Validate
class Vod(PartialGAPIJSON[vod_models.VodModel]):
    """Vod file."""

    # Occurs when the user imports an invalid movie url.
    # TODO: Validate
    @override
    def _get_ACCEPTABLE_ERROR(self) -> str | None:
        return "Unexpected response status code: 404"
    API_ENDPOINT = diving_board().vod

    # TODO: Validate
    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _fetch(self) -> vod_models.VodModel:
        return diving_board().vod.download_and_parse(int(self.unique_identifier))


# TODO: Validate
class Series(PartialGAPIJSON[series_models.SeriesModel]):
    """Series file."""

    # Occurs when the user imports an invalid series url.
    # TODO: Validate
    @override
    def _get_ACCEPTABLE_ERROR(self) -> str | None:
        return "Unexpected response status code: 404"
    API_ENDPOINT = diving_board().series

    # TODO: Validate
    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _fetch(self) -> series_models.SeriesModel:
        return diving_board().series.download_and_parse(int(self.unique_identifier))


# TODO: Validate
class Schedule(GAPIListJSON[schedule_models.ScheduleModel]):
    """Schedule file."""

    API_ENDPOINT = diving_board().schedule

    # TODO: Validate
    @override
    def _fetch(self) -> list[schedule_models.ScheduleModel]:
        # Start at the first of the month because it matches the normal API calls.
        from_ = self.identifier_datetime().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return diving_board().schedule.download_and_parse_until_datetime(
            from_=from_,
            end_datetime=tz_datetime.now(),
        )


# TODO: Validate
class Search(GAPIJSON[search_models.SearchModel]):
    """Search file."""

    API_ENDPOINT = diving_board().search


# TODO: Validate
class FileMixin(MediaTypeMixin, BasePlugin, register=False):
    """The files a title is read out of."""

    # TODO: Validate
    def _is_movie(self) -> bool:
        if self._media_type_value not in ("Movie", "Series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)

        return self._media_type_value == "Movie"

    # TODO: Validate
    def season_file(self, season_key: str | int) -> Season:
        """Return a cached Season for the given season key."""
        key = str(season_key)
        return self._file(Season, key)

    # TODO: Validate
    def vod_file(self, vod_key: str | int) -> Vod:
        """Return a cached Vod for the given vod key."""
        key = str(vod_key)
        return self._file(Vod, key)

    # TODO: Validate
    def series_file(self, series_key: str | int) -> Series:
        """Return a cached Series for the given series key."""
        key = str(series_key)
        return self._file(Series, key)

    # TODO: Validate
    def schedule_file(self, input_date: datetime | File) -> Schedule:
        """Return a cached Schedule for the given datetime or existing File."""
        if isinstance(input_date, File):
            identifier = Schedule.file_key_to_unique_identifier(input_date.key)
        else:
            identifier = input_date.isoformat()
        return self._file(Schedule, identifier)

    # TODO: Validate
    def search_file(self, query: str) -> Search:
        """Return a cached Search for the given query."""
        return self._file(Search, query)

    # TODO: Validate
    def get_latest_schedule_file(self) -> Schedule | None:
        """Return the latest schedule file, or None if none exists."""
        if file := self.preload_latest_file(Schedule):
            return self.schedule_file(file)
        return None

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[Schedule]:
        if file := self.get_latest_schedule_file():
            return [file]
        return []

    # TODO: Validate
    @staticmethod
    def _series_season_items(
        series_data: series_models.SeriesModel,
    ) -> list[series_models.Item1]:
        """Return the list of seasons from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.seasons:
                return element.attributes.seasons.items
        msg = "No seasons element found in series file."
        raise ValueError(msg)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.vod_file(show_key)]
        return [self.series_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.vod_file(season_key)]
        # The season file detects new episodes and changes to the season.
        return [self.season_file(season_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.vod_file(episode_key)]
        # The vod file detects changes to the episode information.
        return [self.vod_file(episode_key), self.season_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [show_key]
        series_data = self.series_file(show_key).parsed()
        return [str(item.id) for item in self._series_season_items(series_data)]

    # TODO: Validate
    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        if self._is_movie():
            return list(season_keys)
        episode_keys: list[str] = []
        for season_key in season_keys:
            season_data = self.season_file(season_key).parsed()
            bucket = diving_board().season.extract_bucket_season(season_data)
            episode_keys.extend(str(item.id) for item in bucket.attributes.items)
        return episode_keys
