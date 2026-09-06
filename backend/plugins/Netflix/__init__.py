# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Netflix.media import NetflixMedia, NetflixMovie, NetflixSeries
from plugins.Netflix.shared import TITLE_URL_REGEX, NetflixShared
from plugins.Netflix.utils import is_movie
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class NetflixInitializer(BasePluginInitializer, NetflixShared): ...


# TODO: Validate
class Netflix(NetflixShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = NetflixInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_importer(self, input: Show | str) -> NetflixMedia:
        if isinstance(input, str):
            match = re.match(self._domain_regex() + TITLE_URL_REGEX, input)
            if not match:
                msg = f"Invalid {self.plugin_name()} URL: {input}"
                raise InvalidURLError(msg)

            # Movies and series are answered at the same address, so the title
            # has to be read before it is known which of the two it is.
            show_key = match.group("title_key")
            self.raise_if_invalid_file(self.title_file(show_key), input)
            if is_movie(self.title_file(show_key).parsed(), show_key):
                return NetflixMovie(self)
            return NetflixSeries(self)

        if not input.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        if input.media_type == "Movie":
            return NetflixMovie(self)
        return NetflixSeries(self)
