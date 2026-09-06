# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Pluto.importer import PlutoImporter, PlutoMovie, PlutoSeries
from plugins.Pluto.shared import MOVIE_URL_REGEX, SERIES_URL_REGEX, PlutoShared
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class PlutoInitializer(BasePluginInitializer, PlutoShared): ...


# TODO: Validate
class Pluto(PlutoShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = PlutoInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, SERIES_URL_REGEX)

    # TODO: Validate
    @override
    def _get_media_importer_from_url(self, url: str) -> PlutoImporter:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return PlutoMovie(self)
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return PlutoSeries(self)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _get_media_importer_from_title(self, title: Title) -> PlutoImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return PlutoMovie(self)
        return PlutoSeries(self)
