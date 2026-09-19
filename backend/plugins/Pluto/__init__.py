# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Pluto.constants import MOVIE_URL_REGEX, SERIES_URL_REGEX
from plugins.Pluto.importer import (
    PlutoImporter,
    PlutoMovieImporter,
    PlutoSeriesImporter,
)
from plugins.Pluto.shared import PlutoShared
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class Pluto(PlutoShared, AbstractPlugin, register=False):
    VIDEO_STORE_SCORE = False
    VIDEO_STORE_POPULARITY = False

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, SERIES_URL_REGEX)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> PlutoImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return PlutoMovieImporter(self.session, self.plugin, self._file_cache)
        return PlutoSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> PlutoImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return PlutoMovieImporter(self.session, self.plugin, self._file_cache)
        return PlutoSeriesImporter(self.session, self.plugin, self._file_cache)
