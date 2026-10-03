# TODO: Validate
from __future__ import annotations

from typing import override

from app.titles.models import Title
from plugins.AdultSwim.linker import AdultSwimLinker
from plugins.AdultSwim.series_importer import AdultSwimSeriesImporter
from plugins.AdultSwim.shared import AdultSwimShared
from plugins.AdultSwim.updater import AdultSwimUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.catalog_support import CatalogSupport


# TODO: Validate
class AdultSwim(
    AdultSwimShared,
    BaseMediaImporterMixin,
    BasePlugin,
    register=True,
):
    CATALOG_SUPPORT = CatalogSupport.yes

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[AdultSwimUpdater]:
        return AdultSwimUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[AdultSwimLinker]:
        return AdultSwimLinker

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> AdultSwimSeriesImporter:
        return AdultSwimSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> AdultSwimSeriesImporter:
        return AdultSwimSeriesImporter(self.session, self.plugin, self._file_cache)
