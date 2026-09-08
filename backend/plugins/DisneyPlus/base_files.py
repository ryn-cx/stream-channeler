# TODO: Validate
from __future__ import annotations

from plugins.DisneyPlus.files import Entity, SeasonEntity
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class DisneyPlusBaseFiles(BasePlugin):
    # TODO: Validate
    def entity_file(self, entity_id: str) -> Entity:
        return self._cached_file(Entity, entity_id)

    # TODO: Validate
    def season_file(self, entity_id: str, season_id: str) -> SeasonEntity:
        return self._cached_file(SeasonEntity, entity_id, season_id)
