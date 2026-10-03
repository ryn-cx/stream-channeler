# TODO: Validate
from __future__ import annotations

import hashlib
from abc import ABC
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.upsert_files import BaseUpsertFilesMixin

if TYPE_CHECKING:
    from app.models import MediaMixin
    from app.seasons.models import Season
    from app.titles.models import Title


# TODO: Validate
def _add_months(value: datetime, months: int) -> datetime:
    years, month_number = divmod(value.month - 1 + months, 12)
    return value.replace(year=value.year + years, month=month_number + 1)


# TODO: Validate
def _seed(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode()).digest())


# TODO: Validate
def staggered_yearly_update_at(key: str, after: datetime) -> datetime:
    """Return an update_at value that occurs yearly on a random day."""
    yearly_date = date(2001, 1, 1) + timedelta(days=_seed(key) % 365)
    update_at = after.replace(month=yearly_date.month, day=yearly_date.day)

    # If the day has already passed this year then the next update should be
    # scheduled for the next year.
    if update_at <= after:
        update_at = _add_months(update_at, 12)
    return update_at


# TODO: Validate
def set_air_date_update_at(record: MediaMixin[Any], air_dates: list[datetime]) -> None:
    # Update a week after the last episode aired to keep airing seasons
    # up-to-date. The maximum value is intentionally not used because some
    # websitees, such as Hulu and TMDB, will list multiple upcoming episodes and
    # using the maximum would delay updates for upcoming episodes.
    for air_date in air_dates:
        record.set_update_at(air_date)
        record.set_update_at(air_date + timedelta(days=7))
        # Buffer days due to possible timestamp offsets
        record.set_update_at(air_date + timedelta(days=8))
        record.set_update_at(air_date + timedelta(days=9))


# TODO: Validate
class BasePluginUpdateAt(BaseUpsertFilesMixin, ABC):
    # TODO: Validate
    def _set_title_update_at(self, title: Title) -> None:
        if not title.data_timestamp:  # Should be impossible.
            msg = f"Record {title.key} has no data_timestamp"
            raise ValueError(msg)
        title.set_update_at(staggered_yearly_update_at(title.key, title.data_timestamp))

    # TODO: Validate
    def _set_season_update_at(self, season: Season) -> None:
        """Set the update_at value for a season.

        The value is determined based on the media type and air dates of the season's
        episodes.
        """
        if not season.data_timestamp:  # Should be impossible
            msg = f"Record {season.key} has no data_timestamp"
            raise ValueError(msg)

        data_timestamp = self._season_files_data_timestamp(
            season.key,
            season.title.key,
        )
        if season.title.media_type != MediaType.movie:
            set_air_date_update_at(
                season,
                [episode.air_date for episode in season.episodes if episode.air_date],
            )
        season.set_update_at(staggered_yearly_update_at(season.key, data_timestamp))
