# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Roku.linker import RokuLinker
from plugins.Roku.movie_importer import RokuMovieImporter
from plugins.Roku.series_importer import RokuSeriesImporter
from plugins.Roku.shared import RokuImporter, RokuShared
from plugins.Roku.updater import RokuUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class Roku(RokuShared, BaseMediaImporterMixin, BasePlugin, register=False):
    CATALOG_SUPPORT = CatalogSupport.no

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[RokuUpdater]:
        return RokuUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[RokuLinker]:
        return RokuLinker

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> RokuImporter:
        content_file = self.content_file(self._url_content_key(url))
        self.raise_invalid_url_if_no_content(content_file, url)
        content = content_file.parsed()
        # A season or an episode belongs to a series, which is what
        # is read and written.
        if content.series is not None:
            return RokuSeriesImporter(self.session, self.plugin, self._file_cache)
        if self.is_movie(content):
            return RokuMovieImporter(self.session, self.plugin, self._file_cache)
        return RokuSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> RokuImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return RokuMovieImporter(self.session, self.plugin, self._file_cache)
        return RokuSeriesImporter(self.session, self.plugin, self._file_cache)
