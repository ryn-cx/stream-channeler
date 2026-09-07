# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.DisneyPlus.importer import (
    DisneyPlusImporter,
    DisneyPlusMovieImporter,
    DisneyPlusSeriesImporter,
)
from plugins.DisneyPlus.shared import ENTITY_URL_REGEX, DisneyPlusShared
from plugins.DisneyPlus.utils import is_movie
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class DisneyPlusInitializer(BasePluginInitializer, DisneyPlusShared): ...


# TODO: Validate
class DisneyPlus(DisneyPlusShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = DisneyPlusInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (ENTITY_URL_REGEX,)

    # TODO: Validate
    @override
    def media_importer_from_url(self, url: str) -> DisneyPlusImporter:
        match = re.match(self._domain_regex() + ENTITY_URL_REGEX, url)
        if not match:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        # Movies and series are answered at the same address, so the page has
        # to be read before it is known which of the two it is.
        title_key = match.group("entity_key")
        self.raise_if_invalid_file(self.entity_file(title_key), url)
        if is_movie(self.entity_file(title_key).parsed()):
            return DisneyPlusMovieImporter(self)
        return DisneyPlusSeriesImporter(self)

    # TODO: Validate
    @override
    def media_importer_from_title(self, title: Title) -> DisneyPlusImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return DisneyPlusMovieImporter(self)
        return DisneyPlusSeriesImporter(self)
