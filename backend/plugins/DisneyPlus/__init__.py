# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.DisneyPlus.movie_importer import DisneyPlusMovieImporter
from plugins.DisneyPlus.series_importer import DisneyPlusSeriesImporter
from plugins.DisneyPlus.shared import (
    DisneyPlusImporter,
    DisneyPlusShared,
    is_movie,
)
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class DisneyPlus(DisneyPlusShared, AbstractPlugin, register=False):
    VIDEO_STORE_SCORE = False
    VIDEO_STORE_POPULARITY = False

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> DisneyPlusImporter:
        title_key = self._url_title_key(url)
        entity_file = self.entity_file(title_key)
        self.raise_invalid_url_if_no_content(entity_file, url)
        if is_movie(entity_file.parsed()):
            return DisneyPlusMovieImporter(self.session, self.plugin, self._file_cache)
        return DisneyPlusSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> DisneyPlusImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return DisneyPlusMovieImporter(self.session, self.plugin, self._file_cache)
        return DisneyPlusSeriesImporter(self.session, self.plugin, self._file_cache)
