# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, override

from app.titles.models import Title
from plugins.AdultSwim.series_importer import AdultSwimSeriesImporter
from plugins.AdultSwim.shared import AdultSwimImporter, AdultSwimShared
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from datetime import datetime


# TODO: Validate
class AdultSwim(AdultSwimShared, AbstractPlugin, register=True):
    VIDEO_STORE_SCORE = False
    VIDEO_STORE_POPULARITY = False

    # TODO: Validate
    @override
    def _next_plugin_update_at(self) -> datetime:
        return max(self._plugin_files_data_timestamps()) + timedelta(days=7)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> AdultSwimImporter:
        return AdultSwimSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> AdultSwimImporter:
        return AdultSwimSeriesImporter(self.session, self.plugin, self._file_cache)
