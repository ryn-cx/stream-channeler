# TODO: Validate
from datetime import datetime
from typing import TypeIs

from app.episodes.models import Episode
from app.models import BaseMediaMixin
from app.seasons.models import Season
from app.titles.models import Title
from plugins.utils.base_plugin.download import BaseDownloadMixin


# TODO: Validate
class BaseOutdatedCheckMixin(BaseDownloadMixin):
    # TODO: Validate
    def _title_is_outdated(
        self,
        title: Title | None,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if title is None or force:
            return True
        return self._record_is_outdated(title, self.title_data_timestamp(title.key))

    # TODO: Validate
    def _season_is_outdated(
        self,
        season: Season | None,
        title_key: str,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if season is None or force:
            return True
        return self._record_is_outdated(
            season,
            self.season_data_timestamp(season.key, title_key),
        )

    # TODO: Validate
    def _episode_is_outdated(
        self,
        episode: Episode | None,
        season_key: str,
        title_key: str,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if episode is None or force:
            return True
        return self._record_is_outdated(
            episode,
            self.episode_data_timestamp(episode.key, season_key, title_key),
        )

    # TODO: Validate
    @staticmethod
    def _record_is_outdated(record: BaseMediaMixin, data_timestamp: datetime) -> bool:
        return record.data_timestamp != data_timestamp or record.deleted_at is not None
