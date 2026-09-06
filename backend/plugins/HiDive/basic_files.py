# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.files.models import File
from plugins.HiDive.files import Schedule, Search, Season, Series, Vod
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def season_file(self, season_key: str | int) -> Season:
        return self._file(Season, str(season_key))

    # TODO: Validate
    def vod_file(self, vod_key: str | int) -> Vod:
        return self._file(Vod, str(vod_key))

    # TODO: Validate
    def search_file(self, query: str) -> Search:
        return self._file(Search, query)

    # TODO: Validate
    def series_file(self, series_key: str | int) -> Series:
        return self._file(Series, str(series_key))

    # TODO: Validate
    def schedule_file(self, input_date: datetime | File) -> Schedule:
        """Return a cached Schedule for the given datetime or existing File."""
        if isinstance(input_date, File):
            identifier = Schedule.file_to_unique_identifier(input_date)
        else:
            identifier = input_date.isoformat()
        return self._file(Schedule, identifier)

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
