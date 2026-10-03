from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.ParamountPlus.constants import MOVIE_URL_REGEX
from plugins.ParamountPlus.linker import ParamountPlusLinker
from plugins.ParamountPlus.movie_importer import ParamountPlusMovieImporter
from plugins.ParamountPlus.series_importer import ParamountPlusSeriesImporter
from plugins.ParamountPlus.shared import ParamountPlusImporter, ParamountPlusShared
from plugins.ParamountPlus.updater import ParamountPlusUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class ParamountPlus(
    ParamountPlusShared,
    BaseMediaImporterMixin,
    BasePlugin,
    register=True,
):
    CATALOG_SUPPORT = CatalogSupport.mostly

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[ParamountPlusUpdater]:
        return ParamountPlusUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[ParamountPlusLinker]:
        return ParamountPlusLinker

    @override
    def _media_importer_from_url(self, url: str) -> ParamountPlusImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return ParamountPlusMovieImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        return ParamountPlusSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._media_importer_from_title(title).similar_title_urls(title)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> ParamountPlusImporter:
        if not title.media_type:  # Should be impossible
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return ParamountPlusMovieImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        return ParamountPlusSeriesImporter(self.session, self.plugin, self._file_cache)
