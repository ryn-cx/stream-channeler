# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Pluto.constants import MOVIE_URL_REGEX
from plugins.Pluto.linker import PlutoLinker
from plugins.Pluto.movie_importer import PlutoMovieImporter
from plugins.Pluto.series_importer import PlutoSeriesImporter
from plugins.Pluto.shared import PlutoImporter, PlutoShared
from plugins.Pluto.updater import PlutoUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class Pluto(PlutoShared, BaseMediaImporterMixin, BasePlugin, register=True):
    CATALOG_SUPPORT = CatalogSupport.mostly

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[PlutoUpdater]:
        return PlutoUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[PlutoLinker]:
        return PlutoLinker

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> PlutoImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return PlutoMovieImporter(self.session, self.plugin, self._file_cache)
        return PlutoSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> PlutoImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return PlutoMovieImporter(self.session, self.plugin, self._file_cache)
        return PlutoSeriesImporter(self.session, self.plugin, self._file_cache)
