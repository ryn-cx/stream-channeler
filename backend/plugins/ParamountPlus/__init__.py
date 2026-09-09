# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.ParamountPlus.importer import (
    ParamountPlusImporter,
    ParamountPlusMovieImporter,
    ParamountPlusSeriesImporter,
)
from plugins.ParamountPlus.shared import ParamountPlusShared
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class ParamountPlus(ParamountPlusShared, BaseImporter, AbstractPlugin, register=False):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @override
    def _validate_url(self, url: str) -> None:
        domain_regex = self._domains_regex()
        for url_regex in (MOVIE_URL_REGEX, TITLE_URL_REGEX):
            if re.match(domain_regex + url_regex, url):
                return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> ParamountPlusImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return ParamountPlusMovieImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        return ParamountPlusSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> ParamountPlusImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return ParamountPlusMovieImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        return ParamountPlusSeriesImporter(self.session, self.plugin, self._file_cache)
