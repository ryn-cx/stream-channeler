from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Amazon.movie_importer import AmazonMovieImporter
from plugins.Amazon.series_importer import AmazonSeriesImporter
from plugins.Amazon.shared import AmazonImporter, AmazonShared
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


class Amazon(AmazonShared, AbstractPlugin, register=True):
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        detail_file = self.detail_file(title.key)
        return detail_file.other_title_urls_on_this_page("Customers also watched")

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
