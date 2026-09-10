# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.DisneyPlus.constants import ENTITY_URL_REGEX
from plugins.DisneyPlus.importer import (
    DisneyPlusImporter,
    DisneyPlusMovieImporter,
    DisneyPlusSeriesImporter,
)
from plugins.DisneyPlus.shared import DisneyPlusShared
from plugins.DisneyPlus.utils import is_movie
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class DisneyPlus(DisneyPlusShared, AbstractPlugin, register=False):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (ENTITY_URL_REGEX,)

    # TODO: Validate
    def _url_title_key(self, url: str) -> str:
        if not (match := re.match(self._domains_regex() + ENTITY_URL_REGEX, url)):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        return match.group("entity_key")

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> DisneyPlusImporter:
        # Movies and series are answered at the same address, so the page has
        # to be read before it is known which of the two it is.
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
        if title.media_type == "Movie":
            return DisneyPlusMovieImporter(self.session, self.plugin, self._file_cache)
        return DisneyPlusSeriesImporter(self.session, self.plugin, self._file_cache)
