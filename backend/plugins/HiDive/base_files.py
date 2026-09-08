# TODO: Validate
from __future__ import annotations

from datetime import datetime
from functools import singledispatchmethod
from typing import TYPE_CHECKING, override

from app.files.models import File
from plugins.HiDive.files import (
    Schedule,
    Search,
    Season,
    Series,
    Vod,
)
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO: Validate
class HiDiveBaseFiles(BasePlugin):
    # TODO: Validate
    def season_file(self, season_key: str | int) -> Season:
        return self._cached_file(Season, str(season_key))

    # TODO: Validate
    def vod_file(self, vod_key: str | int) -> Vod:
        return self._cached_file(Vod, str(vod_key))

    # TODO: Validate
    def search_file(self, query: str) -> Search:
        return self._cached_file(Search, query)

    # TODO: Validate
    def series_file(self, series_key: str | int) -> Series:
        return self._cached_file(Series, str(series_key))

    # TODO: Validate
    @singledispatchmethod
    def schedule_file(self, input_date: datetime | File) -> Schedule:  # noqa: ARG002
        """Return a cached Schedule for the given datetime or existing File."""
        raise TypeError

    # TODO: Validate
    @schedule_file.register
    def _schedule_file_by_datetime(self, input_date: datetime) -> Schedule:
        return self._cached_file(Schedule, input_date.isoformat())

    # TODO: Validate
    @schedule_file.register
    def _schedule_file_by_record(self, input_date: File) -> Schedule:
        return self._cached_file(
            Schedule,
            Schedule.file_to_unique_identifier(input_date),
        )

    # TODO: Validate
    def get_latest_schedule_file(self) -> Schedule | None:
        """Return the latest schedule file, or None if none exists."""
        if file := self.latest_file_record(Schedule):
            return self.schedule_file(file)
        return None

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[Schedule]:
        if file := self.get_latest_schedule_file():
            return [file]
        return []
