from datetime import datetime
from typing import TypeIs

from app.episodes.models import Episode
from app.models import BaseMediaMixin
from app.seasons.models import Season
from app.shows.models import Show
from plugins.utils.base_plugin_v2.download import BaseDownloadMixin


class BaseOutdatedCheckMixin(BaseDownloadMixin):
    def _show_is_outdated(
        self,
        show: Show | None,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if show is None or force:
            return True
        return self._record_is_outdated(show, self.show_data_timestamp(show.key))

    def _season_is_outdated(
        self,
        season: Season | None,
        show_key: str,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if season is None or force:
            return True
        return self._record_is_outdated(
            season,
            self.season_data_timestamp(season.key, show_key),
        )

    def _episode_is_outdated(
        self,
        episode: Episode | None,
        season_key: str,
        show_key: str,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if episode is None or force:
            return True
        return self._record_is_outdated(
            episode,
            self.episode_data_timestamp(episode.key, season_key, show_key),
        )

    @staticmethod
    def _record_is_outdated(record: BaseMediaMixin, data_timestamp: datetime) -> bool:
        return record.data_timestamp != data_timestamp or record.deleted_at is not None
