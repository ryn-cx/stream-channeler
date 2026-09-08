# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Tubi.constants import EPISODE_URL_REGEX, MOVIE_URL_REGEX, SERIES_URL_REGEX
from plugins.Tubi.importer import TubiImporter, TubiMovieImporter, TubiSeriesImporter
from plugins.Tubi.shared import TubiShared
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class TubiInitializer(BasePluginInitializer, TubiShared): ...


# TODO: Validate
class Tubi(TubiShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = TubiInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    @override
    def media_importer_from_url(self, url: str) -> TubiImporter:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return TubiMovieImporter(self)
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return TubiSeriesImporter(self)
        # An episode address names the series it belongs to, which is what
        # is read and written.
        if re.match(domain_regex + EPISODE_URL_REGEX, url):
            return TubiSeriesImporter(self)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def media_importer_from_title(self, title: Title) -> TubiImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return TubiMovieImporter(self)
        return TubiSeriesImporter(self)
