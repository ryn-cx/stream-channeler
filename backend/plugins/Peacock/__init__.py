# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Peacock.linker import PeacockLinker
from plugins.Peacock.movie_importer import PeacockMovieImporter
from plugins.Peacock.series_importer import PeacockSeriesImporter
from plugins.Peacock.shared import PeacockImporter, PeacockShared
from plugins.Peacock.updater import PeacockUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class Peacock(PeacockShared, BaseMediaImporterMixin, BasePlugin, register=True):
    CATALOG_SUPPORT = CatalogSupport.yes

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[PeacockUpdater]:
        return PeacockUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[PeacockLinker]:
        return PeacockLinker

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> PeacockImporter:
        title_key = self.title_key_from_url(url)
        if not self.is_series_key(title_key):
            # A series and a movie are served by endpoints of their own, so a
            # UUID key is a movie when the movie endpoint has something for it.
            movie_file = self.movie_file(title_key)
            movie_file.download_if_outdated()
            if movie_file.record_content:
                return PeacockMovieImporter(
                    self.session,
                    self.plugin,
                    self._file_cache,
                )
        return PeacockSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> PeacockImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return PeacockMovieImporter(self.session, self.plugin, self._file_cache)
        return PeacockSeriesImporter(self.session, self.plugin, self._file_cache)
