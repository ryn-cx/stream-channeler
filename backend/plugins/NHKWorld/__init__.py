# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.NHKWorld.linker import NHKWorldLinker
from plugins.NHKWorld.series_importer import NHKWorldSeriesImporter
from plugins.NHKWorld.shared import NHKWorldShared
from plugins.NHKWorld.updater import NHKWorldUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class NHKWorld(
    NHKWorldShared,
    BaseMediaImporterMixin,
    BasePlugin,
    register=True,
):
    CATALOG_SUPPORT = CatalogSupport.yes

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[NHKWorldUpdater]:
        return NHKWorldUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[NHKWorldLinker]:
        return NHKWorldLinker

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> NHKWorldSeriesImporter:
        return NHKWorldSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> NHKWorldSeriesImporter:
        return NHKWorldSeriesImporter(self.session, self.plugin, self._file_cache)
