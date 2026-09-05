# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Tubi.media import TubiMedia, TubiMovie, TubiSeries
from plugins.Tubi.shared import (
    EPISODE_URL_REGEX,
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    TubiShared,
)
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin_v3.base import BaseReadURL
from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.shows.models import Show


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
    def get_media_importer(self, input: Show | str) -> TubiMedia:
        if isinstance(input, str):
            domain_regex = self._domain_regex()
            if re.match(domain_regex + MOVIE_URL_REGEX, input):
                return TubiMovie(self)
            if re.match(domain_regex + SERIES_URL_REGEX, input):
                return TubiSeries(self)
            # An episode address names the series it belongs to, which is what
            # is read and written.
            if re.match(domain_regex + EPISODE_URL_REGEX, input):
                return TubiSeries(self)

            msg = f"Invalid {self.plugin_name()} URL: {input}"
            raise InvalidURLError(msg)

        if not input.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        if input.media_type == "Movie":
            return TubiMovie(self)
        return TubiSeries(self)
