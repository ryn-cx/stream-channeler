from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, TypeIs

from plugins.utils.base_plugin.file_access import BaseFileAccessMixin

if TYPE_CHECKING:
    from datetime import datetime

    from app.episodes.models import Episode
    from app.models import BaseMediaMixin
    from app.seasons.models import Season
    from app.titles.models import Title


class BaseOutdatedMixin(BaseFileAccessMixin, ABC):
    def _title_is_outdated(
        self,
        title: Title | None,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        """Return True if the title is outdated.

        TypeIs[None] tells the type checker that if the title is up to date it must be
        an actual `Title` and it cannot be None.

        A title is considered outdated if a title file is newer than the title's data
        timestamp.
        """
        if title is None or force:
            return True
        return self._record_is_outdated(
            title,
            self._title_files_data_timestamp(title.key),
        )

    def _season_is_outdated(
        self,
        season: Season | None,
        title_key: str,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        """Return True if the season is outdated.

        TypeIs[None] tells the type checker that if the season is up to date it must be
        an actual `Season` and it cannot be None.

        A season is considered outdated if a season file is newer than the season's data
        timestamp.
        """
        if season is None or force:
            return True
        return self._record_is_outdated(
            season,
            self._season_files_data_timestamp(season.key, title_key),
        )

    def _episode_is_outdated(
        self,
        episode: Episode | None,
        season_key: str,
        title_key: str,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        """Return True if the episode is outdated.

        TypeIs[None] tells the type checker that if the episode is up to date it must be
        an actual `Episode` and it cannot be None.

        An episode is considered outdated if an episode file is newer than the episode's
        data timestamp.
        """
        if episode is None or force:
            return True
        return self._record_is_outdated(
            episode,
            self._episode_files_data_timestamp(episode.key, season_key, title_key),
        )

    @staticmethod
    def _record_is_outdated(
        record: BaseMediaMixin,
        minimum_timestamp: datetime,
    ) -> bool:
        """Return True if the record is outdated.

        A record is considered outdated if its timestamp is less than the provided
        minimum_timestamp.
        """
        if not record.data_timestamp:
            msg = "Record has no data timestamp."
            raise ValueError(msg)

        return record.data_timestamp < minimum_timestamp
