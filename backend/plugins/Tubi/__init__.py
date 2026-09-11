# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Tubi.constants import EPISODE_URL_REGEX, MOVIE_URL_REGEX, SERIES_URL_REGEX
from plugins.Tubi.importer import TubiImporter, TubiMovieImporter, TubiSeriesImporter
from plugins.Tubi.shared import TubiShared
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class Tubi(TubiShared, AbstractPlugin, register=True):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> TubiImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return TubiMovieImporter(self.session, self.plugin, self._file_cache)
        # An episode address names the series it belongs to, which is what
        # is read and written.
        return TubiSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> TubiImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return TubiMovieImporter(self.session, self.plugin, self._file_cache)
        return TubiSeriesImporter(self.session, self.plugin, self._file_cache)
