# TODO: Validate
from datetime import datetime
from typing import TypeIs

from app.episodes.models import Episode
from app.models import BaseMediaMixin
from app.seasons.models import Season
from app.shows.models import Show
from plugins.utils.base_plugin.download import DownloadMixin


class CheckMixin(DownloadMixin):
    def _show_is_outdated(
        self,
        show: Show | None,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        """Report whether the show is missing, stale, or soft deleted."""
        if show is None or force:
            return True
        return self._record_is_outdated(show, self.show_data_timestamp(show.key))

    def _season_is_outdated(
        self,
        season: Season | None,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        """Report whether the season is missing, stale, or soft deleted."""
        if season is None or force:
            return True
        return self._record_is_outdated(
            season,
            self.season_data_timestamp(season.key, season.show.key),
        )

    def _episode_is_outdated(
        self,
        episode: Episode | None,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        """Report whether the episode is missing, stale, or soft deleted."""
        if episode is None or force:
            return True
        return self._record_is_outdated(
            episode,
            self.episode_data_timestamp(
                episode.key,
                episode.season.key,
                episode.season.show.key,
            ),
        )

    @staticmethod
    def _record_is_outdated(
        record: BaseMediaMixin,
        data_timestamp: datetime,
    ) -> bool:
        """Report whether a record's data is stale or the record is soft deleted."""
        return record.data_timestamp != data_timestamp or record.deleted_at is not None
