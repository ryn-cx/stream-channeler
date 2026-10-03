from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Amazon.linker import AmazonLinker
from plugins.Amazon.movie_importer import AmazonMovieImporter
from plugins.Amazon.series_importer import AmazonSeriesImporter
from plugins.Amazon.shared import AmazonImporter, AmazonShared
from plugins.Amazon.updater import AmazonUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class Amazon(
    AmazonShared,
    BaseMediaImporterMixin,
    BasePlugin,
    register=True,
):
    CATALOG_SUPPORT = CatalogSupport.mostly

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[AmazonUpdater]:
        return AmazonUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[AmazonLinker]:
        return AmazonLinker

    # TODO: Validate
    def _amazon_updater(self) -> AmazonUpdater:
        return AmazonUpdater(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._amazon_updater().similar_title_urls(title)

    @override
    def _media_importer_from_url(self, url: str) -> AmazonImporter:
        link_id = self.link_id_from_url(url)
        self.raise_invalid_url_if_no_content(self.detail_file(link_id), url)
        if self.detail_file(link_id).parsed().entity_type == "Movie":
            return AmazonMovieImporter(self.session, self.plugin, self._file_cache)
        return AmazonSeriesImporter(self.session, self.plugin, self._file_cache)

    @override
    def _media_importer_from_title(self, title: Title) -> AmazonImporter:
        if not title.media_type:  # Should be impossible.
            msg = "Title.media_type is not set."
            raise AttributeError(msg)

        if title.media_type == MediaType.movie:
            return AmazonMovieImporter(self.session, self.plugin, self._file_cache)
        return AmazonSeriesImporter(self.session, self.plugin, self._file_cache)
