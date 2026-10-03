from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HiDive.constants import SEASON_URL_REGEX, SERIES_URL_REGEX
from plugins.HiDive.linker import HiDiveLinker
from plugins.HiDive.movie_importer import HiDiveMovieImporter
from plugins.HiDive.series_importer import HiDiveSeriesImporter
from plugins.HiDive.shared import HiDiveShared
from plugins.HiDive.updater import HiDiveUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class HiDive(HiDiveShared, BaseMediaImporterMixin, BasePlugin, register=True):
    CATALOG_SUPPORT = CatalogSupport.yes

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[HiDiveUpdater]:
        return HiDiveUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[HiDiveLinker]:
        return HiDiveLinker

    # TODO: Validate
    def _hidive_updater(self) -> HiDiveUpdater:
        return HiDiveUpdater(self.session, self.plugin, self._file_cache)

    @override
    def _media_importer_from_url(
        self,
        url: str,
    ) -> HiDiveSeriesImporter | HiDiveMovieImporter:
        domain_regex = self._domains_regex()
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return HiDiveSeriesImporter(self.session, self.plugin, self._file_cache)
        if re.match(domain_regex + SEASON_URL_REGEX, url):
            return HiDiveSeriesImporter(self.session, self.plugin, self._file_cache)
        return HiDiveMovieImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(
        self,
        title: Title,
    ) -> HiDiveSeriesImporter | HiDiveMovieImporter:
        if not title.media_type:  # Should be impossible
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return HiDiveMovieImporter(self.session, self.plugin, self._file_cache)
        return HiDiveSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._hidive_updater().similar_title_urls(title)
