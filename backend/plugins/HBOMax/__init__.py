# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HBOMax.constants import MOVIE_URL_REGEX
from plugins.HBOMax.linker import HBOMaxLinker
from plugins.HBOMax.movie_importer import HBOMaxMovieImporter
from plugins.HBOMax.series_importer import HBOMaxSeriesImporter
from plugins.HBOMax.shared import HBOMaxImporter, HBOMaxShared
from plugins.HBOMax.updater import HBOMaxUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class HBOMax(HBOMaxShared, BaseMediaImporterMixin, BasePlugin, register=True):
    CATALOG_SUPPORT = CatalogSupport.mostly

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[HBOMaxUpdater]:
        return HBOMaxUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[HBOMaxLinker]:
        return HBOMaxLinker

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> HBOMaxImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return HBOMaxMovieImporter(self.session, self.plugin, self._file_cache)
        return HBOMaxSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._media_importer_from_title(title).similar_title_urls(title)

    # TODO: Validate
    @override
    def _media_importer_from_title(
        self,
        title: Title,
    ) -> HBOMaxMovieImporter | HBOMaxSeriesImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return HBOMaxMovieImporter(self.session, self.plugin, self._file_cache)
        return HBOMaxSeriesImporter(self.session, self.plugin, self._file_cache)
