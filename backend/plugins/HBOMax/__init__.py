# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HBOMax.importer import HBOMaxImporter, HBOMaxMovie, HBOMaxSeries
from plugins.HBOMax.shared import MOVIE_URL_REGEX, TITLE_URL_REGEX, HBOMaxShared
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
    def _get_media_importer_from_url(self, url: str) -> HBOMaxImporter:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return HBOMaxMovie(self)
        if re.match(domain_regex + TITLE_URL_REGEX, url):
            return HBOMaxSeries(self)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _get_media_importer_from_title(self, title: Title) -> HBOMaxImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return HBOMaxMovie(self)
        return HBOMaxSeries(self)
