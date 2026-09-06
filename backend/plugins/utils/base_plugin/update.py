# TODO: Validate
"""Reading a stored title again, and saying when it should be read next."""

from __future__ import annotations

from abc import ABC
from collections.abc import Iterable
from datetime import datetime, timedelta

from app.episodes.preload import preload_episodes
from app.seasons.models import Season
from app.titles.models import Title
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.utils.base_plugin.soft_delete import BaseSoftDeleteMixin


# TODO: Validate
class BaseUpdateMixin(BaseSoftDeleteMixin, ABC):
    # TODO: Validate
    def _mark_changed_titles_for_update(
        self,
        listed_title_keys: Iterable[str],
        source_key: str | None = None,
    ) -> None:
        listed = set(listed_title_keys)
        data_timestamp = self.source_data_timestamp()
        for source in self._preload_sources(source_key, preload_titles=True):
            for title in source.titles:
                is_listed = title.key in listed
                is_deleted = title.deleted_at is not None
                if is_listed == is_deleted:
                    title.set_update_at(data_timestamp)

    # TODO: Validate
    def _set_weekly_updates_from_episodes(
        self,
        title: Title,
        *,
        update_title: bool = True,
        update_seasons: bool = True,
    ) -> None:
        """Set update_at on the `Title`/`Season` based on `Episode.air_date`.

        `update_at` will be set to be a week after the latest `Episode.air_date` if
        that is a better `update_at` value than the current `update_at` value.
        """
        preload_episodes(self.session, [title])
        for season in title.active_children:
            for episode in season.active_children:
                if episode.air_date:
                    update_at = episode.air_date + timedelta(days=7)
                    if update_seasons:
                        season.set_update_at(update_at)
                    if update_title:
                        title.set_update_at(update_at)

    # TODO: Validate
    def _set_dynamic_update_at(self, title: Title) -> None:
        preload_episodes(self.session, [title])
        title_air_dates: list[datetime] = []
        for season in title.active_children:
            season_air_dates = [
                episode.air_date
                for episode in season.active_children
                if episode.air_date
            ]
            self._try_update_at_values(season, season_air_dates)
            title_air_dates += season_air_dates
        self._try_update_at_values(title, title_air_dates)

    # TODO: Validate
    @staticmethod
    def _try_update_at_values(
        record: Title | Season,
        air_dates: list[datetime],
    ) -> None:
        now = tz_datetime.now()
        for air_date in air_dates:
            if air_date > now:
                record.set_update_at(air_date)
        if air_dates:
            record.set_update_at(max(air_dates) + timedelta(days=7))
        if record.data_timestamp:
            record.set_update_at(
                staggered_monthly_update_at(record.key, record.data_timestamp),
            )

    # TODO: Validate
    def _update_and_upsert_title(
        self,
        title: Title,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        """Update all files then upsert the title.

        Title files are updated using Title.udpate and the File.update_at values.
        Season files are updated using Season.update and the File.update_at values.
        Episode files are updated using Episode.update and the File.update_at values.
        """
        self._download_title_files_and_children(title.key, update_at)
        self._preload_title(title.id, preload_episodes=True).one()
        self.upsert_title(title.source, title.key, force=force)
