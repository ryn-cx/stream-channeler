# TODO: Validate
from __future__ import annotations

from plugins.Pluto.files import ItemsFile, SeasonsFile
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class PlutoBaseFiles(BasePlugin):
    # TODO: Validate
    def items_file(self, item_id: str) -> ItemsFile:
        """Contains the metadata of a single on-demand movie."""
        return self._file(ItemsFile, item_id)

    # TODO: Validate
    def seasons_file(self, series_id: str) -> SeasonsFile:
        """Contains a series' metadata, its seasons, and all of their episodes."""
        return self._file(SeasonsFile, series_id)
