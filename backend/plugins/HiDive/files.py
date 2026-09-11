# TODO: Validate
"""The files a HiDive title is read out of."""

from __future__ import annotations

import json
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
from plugins.utils.base_plugin.files import (
    PagedEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.constants import INCOMPLETE_STATUS
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def diving_board() -> DivingBoard:
    return DivingBoard(get_around_client=get_around_client())


# TODO: Validate
class Season(SingleArgEndpointFile[season_models.SeasonModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SeasonEndpoint:
        return diving_board().season

    # Occurs when the user imports an invalid TV title url.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeasonNotFoundError)


# TODO: Validate
class Vod(SingleArgEndpointFile[vod_models.VodModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> VodEndpoint:
        return diving_board().vod

    # Occurs when the user imports an invalid movie url.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, VodNotFoundError)


# TODO: Validate
class Series(SingleArgEndpointFile[series_models.SeriesModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SeriesEndpoint:
        return diving_board().series

    # Occurs when the user imports an invalid series url.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


# TODO: Validate
class Schedule(PagedEndpointFile[schedule_models.ScheduleModel]):
    # TODO: Validate
    @override
    def _initial_status_after_downloading(self) -> str:
        return INCOMPLETE_STATUS

    # TODO: Validate
    @override
    def _endpoint(self) -> ScheduleEndpoint:  # type: ignore[override]
        return diving_board().schedule

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # Start at the first of the month because it matches the normal API calls.
        from_ = tz_datetime.fromisoformat(self.unique_identifier).replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return json.dumps(self._endpoint().download_all(from_))


# TODO: Validate
class Search(SingleArgEndpointFile[search_models.SearchModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SearchEndpoint:
        return diving_board().search
