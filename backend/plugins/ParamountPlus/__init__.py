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
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class ParamountPlusInitializer(BasePluginInitializer, ParamountPlusShared): ...


# TODO: Validate
class ParamountPlus(ParamountPlusShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = ParamountPlusInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> ParamountPlusImporter:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return ParamountPlusMovieImporter(self)
        if re.match(domain_regex + TITLE_URL_REGEX, url):
            return ParamountPlusSeriesImporter(self)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> ParamountPlusImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return ParamountPlusMovieImporter(self)
        return ParamountPlusSeriesImporter(self)
