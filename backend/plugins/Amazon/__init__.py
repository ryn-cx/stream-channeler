from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Amazon.importer import (
    AmazonImporter,
    AmazonMovieImporter,
    AmazonSeriesImporter,
)
from plugins.Amazon.shared import AmazonShared
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from app.titles.models import Title


class Amazon(AmazonShared, AbstractPlugin, register=True):
    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> list[str]:
        return list(
            self.detail_file(title.key).other_title_urls_on_this_page(
                "Customers also watched",
            ),
        )

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

        if title.media_type == "Movie":
            return AmazonMovieImporter(self.session, self.plugin, self._file_cache)
        return AmazonSeriesImporter(self.session, self.plugin, self._file_cache)
