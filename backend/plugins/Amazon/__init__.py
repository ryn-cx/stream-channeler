# TODO: Validate
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


# TODO: Validate
class Amazon(AmazonShared, AbstractPlugin, register=True):
    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> AmazonImporter:
        link_id = self.link_id_from_url(url)
        self.raise_invalid_url_if_no_content(self.detail_file(link_id), url)
        if self._is_movie(link_id):
            return AmazonMovieImporter(self.session, self.plugin, self._file_cache)
        return AmazonSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> AmazonImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return AmazonMovieImporter(self.session, self.plugin, self._file_cache)
        return AmazonSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    def _is_movie(self, link_id: str) -> bool:
        return self.detail_file(link_id).entity_type() == "Movie"
