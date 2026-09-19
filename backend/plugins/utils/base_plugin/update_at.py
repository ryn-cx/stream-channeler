# TODO: Validate
from __future__ import annotations

import hashlib
from abc import ABC
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.file_access import BaseFileAccessMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.preload import BasePreloadMixin

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.seasons.models import Season
    from app.titles.models import Title


# TODO: Validate
class BasePluginUpdateAt(
    BaseFileAccessMixin,
    BasePreloadMixin,
    AbstractPlugin,
    ABC,
):
    # TODO: Validate
    def _mark_mismatched_titles_as_outdated(
        self,
        source_key: str | None,
        new_title_keys: Iterable[str],
        data_timestamp: datetime,
    ) -> None:
        """Mark `Title`s as outdated if they are mismatched with the `new_title_keys`.

        Mismatched means one of the following:
            Title is listed in new_title_keys but is marked as deleted
            Title is not in new_title_keys but is not marked as deleted.
        """
        new_title_keys = set(new_title_keys)
        for source in self._preload_sources(source_key, preload_titles=True):
            for title in source.titles:
                is_listed = title.key in new_title_keys
                is_deleted = title.deleted_at is not None
                if is_listed == is_deleted:
                    title.set_update_at(data_timestamp)

    # TODO: Validate
    @staticmethod
    def _add_months(value: datetime, months: int) -> datetime:
        years, month_number = divmod(value.month - 1 + months, 12)
        return value.replace(year=value.year + years, month=month_number + 1)

    @classmethod
    def _staggered_monthly_update_at(
        cls,
        key: str,
        data_timestamp: datetime,
        months: int = 1,
    ) -> datetime:
        """Return an update_at value that occurs monthly on a random day."""
        seed = int.from_bytes(hashlib.sha256(key.encode()).digest())
        # Increment by 1 because modulo returns 0 to n-1.
        monthly_day = (seed % 28) + 1
        update_at = data_timestamp.replace(day=monthly_day)

        # if the day has already passed this month then the next update should be
        # schedule for the next month.
        if update_at <= data_timestamp:
            update_at = cls._add_months(update_at, 1)
        return cls._add_months(update_at, months - 1)

    @classmethod
    def _staggered_yearly_update_at(
        cls,
        key: str,
        data_timestamp: datetime,
    ) -> datetime:
        """Return an update_at value that occurs yearly on a random day."""
        seed = int.from_bytes(hashlib.sha256(key.encode()).digest())
        yearly_date = date(2001, 1, 1) + timedelta(days=seed % 365)
        update_at = data_timestamp.replace(month=yearly_date.month, day=yearly_date.day)

        # If the day has already passed this year then the next update should be
        # scheduled for the next year.
        if update_at <= data_timestamp:
            update_at = cls._add_months(update_at, 12)
        return update_at

    @classmethod
    def _episode_based_update_at(
        cls,
        key: str,
        air_dates: list[datetime],
        data_timestamp: datetime,
    ) -> datetime:
        """Return an update_at value based on the air dates of episodes.

        The more recent the last episode, the more frequent the updates.
        - If the last episode aired within the past year, updates occur monthly.
        - If the last episode aired within the past two years, updates occur every two
        months.
        - etc.

        The maximum time between updates is 12 months.
        """
        # If an air date is found update monthly based on the last episode's air
        # date. If it was in the last year update it monthly, if it was in the last
        # 2 years update it every 2 months, etc. The maximum time between updates is
        # 12 months.
        if air_dates:
            max_date = max(air_dates)
            years_since_last_episode = (data_timestamp - max_date).days // 365
            months = min(max(years_since_last_episode + 1, 1), 12)
        # If no air dates are found update once a year to check for changes in
        # availability.
        else:
            months = 12
        return cls._staggered_monthly_update_at(key, data_timestamp, months)

    def _set_title_update_at(self, title: Title) -> None:
        """Set the update_at value for a title.

        The value is determined based on the media type and air dates of titles'
        episodes.
        """
        if not title.data_timestamp:  # Should be impossible.
            msg = f"Record {title.key} has no data_timestamp"
            raise ValueError(msg)

        if title.media_type == MediaType.movie:
            # Movies are updates once a year to check for changes in availability.
            title.set_update_at(
                self._staggered_yearly_update_at(title.key, title.data_timestamp),
            )
        else:
            air_dates = [
                episode.air_date
                for season in title.seasons
                for episode in season.episodes
                if episode.air_date
            ]
            title.set_update_at(
                self._episode_based_update_at(
                    title.key,
                    air_dates,
                    title.data_timestamp,
                ),
            )

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
        # Movies are updates once a year to check for changes in availability.
        if season.title.media_type == MediaType.movie:
            update_at = self._staggered_yearly_update_at(season.key, data_timestamp)
            season.set_update_at(update_at)
        else:
            air_dates = [
                episode.air_date for episode in season.episodes if episode.air_date
            ]
            # Update a week after the last episode aired to keep airing seasons
            # up-to-date. The maximum value is intentionally not used because some
            # websitees, such as Hulu and TMDB, will list multiple upcoming episodes and
            # using the maximum would delay updates for upcoming episodes.
            for air_date in air_dates:
                season.set_update_at(air_date)
                season.set_update_at(air_date + timedelta(days=7))
                # Buffer days due to possible timestamp offsets
                season.set_update_at(air_date + timedelta(days=8))
                season.set_update_at(air_date + timedelta(days=9))
            season.set_update_at(
                self._episode_based_update_at(
                    season.key,
                    air_dates,
                    data_timestamp,
                )
            )
