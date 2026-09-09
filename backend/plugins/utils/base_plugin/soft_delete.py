from __future__ import annotations

from abc import ABC

from plugins.utils.base_plugin.file_access import BaseFileAccessMixin
from plugins.utils.base_plugin.preload import BasePreloadMixin


class BaseSoftDeleteMixin(BaseFileAccessMixin, BasePreloadMixin, ABC):
    def soft_delete_missing_seasons(self, title_key: str) -> None:
        """Soft-delete seasons whose keys are not in the title's season file."""
        season_keys = self._season_keys_from_title_files(title_key)
        for title in self._preload_title(title_key, preload_seasons=True).all():
            title.soft_delete_missing_children(season_keys)

    def _soft_delete_missing_episodes(self, season_key: str, title_key: str) -> None:
        """Soft-delete episodes whose keys are not in the season's episode file."""
        episode_keys = self._episode_keys_from_season_files(season_key, title_key)
        for title in self._preload_title(title_key, preload_seasons=True).all():
            for season in title.seasons:
                if season.key == season_key:
                    season.soft_delete_missing_children(episode_keys)

    def _soft_delete_missing_seasons_and_episodes(self, title_key: str) -> None:
        """Soft-delete all missing seasons and episodes for the given title."""
        self.soft_delete_missing_seasons(title_key)
        for season_key in self._season_keys_from_title_files(title_key):
            self._soft_delete_missing_episodes(season_key, title_key)
