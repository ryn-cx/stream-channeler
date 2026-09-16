# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HBOMax.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.HBOMax.importer import (
    HBOMaxImporter,
    HBOMaxMovieImporter,
    HBOMaxSeriesImporter,
)
from plugins.HBOMax.shared import HBOMaxShared
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class HBOMax(HBOMaxShared, AbstractPlugin, register=True):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> HBOMaxImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return HBOMaxMovieImporter(self.session, self.plugin, self._file_cache)
        return HBOMaxSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> list[str]:
        return self._media_importer_from_title(title).similar_title_urls(title)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> HBOMaxImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return HBOMaxMovieImporter(self.session, self.plugin, self._file_cache)
        return HBOMaxSeriesImporter(self.session, self.plugin, self._file_cache)
