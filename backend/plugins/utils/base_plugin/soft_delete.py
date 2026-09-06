# TODO: Validate
"""Marking away the rows a website no longer lists."""

from __future__ import annotations

from abc import ABC

from app.seasons.models import Season
from app.shows.models import Show
from plugins.utils.base_plugin.preload import BasePreloadMixin
from plugins.utils.base_plugin.upsert import BaseUpsertMixin


# TODO: Validate
class BaseSoftDeleteMixin(BaseUpsertMixin, BasePreloadMixin, ABC):
    # TODO: Validate
    def soft_delete_missing_seasons(self, show_key: str) -> None:
        """Soft-delete seasons whose keys are not in the show's season file."""
        season_keys = self._season_keys_from_show_files(show_key)
        source_ids = {source.id for source in self.plugin.sources}
        for obj in list(self.session.identity_map.values()):
            if (
                isinstance(obj, Show)
                and obj.key == show_key
                and obj.source_id in source_ids
            ):
                obj.soft_delete_missing_children(season_keys)

    # TODO: Validate
    def soft_delete_missing_episodes(self, season_key: str, show_key: str) -> None:
        """Soft-delete episodes whose keys are not in the season's episode file."""
        episode_keys = self._episode_keys_from_season_files(season_key, show_key)
        source_ids = {source.id for source in self.plugin.sources}
        show_ids = {
            obj.id
            for obj in self.session.identity_map.values()
            if isinstance(obj, Show) and obj.source_id in source_ids
        }
        for obj in list(self.session.identity_map.values()):
            if (
                isinstance(obj, Season)
                and obj.key == season_key
                and obj.show_id in show_ids
            ):
                obj.soft_delete_missing_children(episode_keys)

    # TODO: Validate
    def _soft_delete_missing(self, show_key: str) -> None:
        _cache = self._preload_show(show_key, preload_episodes=True).all()
        self.soft_delete_missing_seasons(show_key)
        for season_key in self._season_keys_from_show_files(show_key):
            self.soft_delete_missing_episodes(season_key, show_key)
