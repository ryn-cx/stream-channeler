# TODO: Validate
"""The files a HiDive title is read out of."""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import cache
from typing import override

from diving_board import DivingBoard
from diving_board.exceptions import (
    SeasonNotFoundError,
    SeriesNotFoundError,
    VodNotFoundError,
)
from diving_board.schedule import Schedule as ScheduleEndpoint
from diving_board.schedule import models as schedule_models
from diving_board.search import Search as SearchEndpoint
from diving_board.search import models as search_models
from diving_board.season import Season as SeasonEndpoint
from diving_board.season import models as season_models
from diving_board.series import Series as SeriesEndpoint
from diving_board.series import models as series_models
from diving_board.vod import Vod as VodEndpoint
from diving_board.vod import models as vod_models

from app.utils import tz_datetime
from plugins.utils.base_plugin_v3.files import EndpointFile, PagedEndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def diving_board() -> DivingBoard:
    return DivingBoard(get_around_client=get_around_client())


# TODO: Validate
class Season(EndpointFile[season_models.SeasonModel]):
    @override
    def _endpoint(self) -> SeasonEndpoint:
        return diving_board().season

    # Occurs when the user imports an invalid TV show url.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeasonNotFoundError)


# TODO: Validate
class Vod(EndpointFile[vod_models.VodModel]):
    @override
    def _endpoint(self) -> VodEndpoint:
        return diving_board().vod

    # Occurs when the user imports an invalid movie url.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, VodNotFoundError)


# TODO: Validate
class Series(EndpointFile[series_models.SeriesModel]):
    @override
    def _endpoint(self) -> SeriesEndpoint:
        return diving_board().series

    # Occurs when the user imports an invalid series url.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


# TODO: Validate
class Schedule(PagedEndpointFile[schedule_models.ScheduleModel]):
    @override
    def _endpoint(self) -> ScheduleEndpoint:
        return diving_board().schedule

    @override
    def _download_pages(self) -> list[str]:
        # Start at the first of the month because it matches the normal API calls.
        from_ = self.identifier_datetime().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return self._endpoint().download_all(from_)


# TODO: Validate
class Search(EndpointFile[search_models.SearchModel]):
    @override
    def _endpoint(self) -> SearchEndpoint:
        return diving_board().search

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)
