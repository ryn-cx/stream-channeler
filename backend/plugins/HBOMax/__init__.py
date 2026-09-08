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
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class HBOMaxInitializer(BasePluginInitializer, HBOMaxShared): ...


# TODO: Validate
class HBOMax(HBOMaxShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = HBOMaxInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @override
    def _validate_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        for url_regex in (MOVIE_URL_REGEX, TITLE_URL_REGEX):
            if re.match(domain_regex + url_regex, url):
                return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> HBOMaxImporter:
        if re.match(self._domain_regex() + MOVIE_URL_REGEX, url):
            return HBOMaxMovieImporter(self)
        return HBOMaxSeriesImporter(self)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> HBOMaxImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return HBOMaxMovieImporter(self)
        return HBOMaxSeriesImporter(self)
