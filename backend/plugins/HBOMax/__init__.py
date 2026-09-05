# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HBOMax.media import HBOMaxMedia, HBOMaxMovie, HBOMaxSeries
from plugins.HBOMax.shared import MOVIE_URL_REGEX, SHOW_URL_REGEX, HBOMaxShared
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin_v3.base import BaseReadURL
from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class HBOMaxInitializer(BasePluginInitializer, HBOMaxShared): ...


# TODO: Validate
class HBOMax(HBOMaxShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = HBOMaxInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, SHOW_URL_REGEX)

    # TODO: Validate
    @override
    def get_media_importer(self, input: Show | str) -> HBOMaxMedia:
        if isinstance(input, str):
            domain_regex = self._domain_regex()
            if re.match(domain_regex + MOVIE_URL_REGEX, input):
                return HBOMaxMovie(self)
            if re.match(domain_regex + SHOW_URL_REGEX, input):
                return HBOMaxSeries(self)

            msg = f"Invalid {self.plugin_name()} URL: {input}"
            raise InvalidURLError(msg)

        if not input.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        if input.media_type == "Movie":
            return HBOMaxMovie(self)
        return HBOMaxSeries(self)
