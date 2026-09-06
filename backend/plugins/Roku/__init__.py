# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Roku.media import RokuMedia, RokuMovie, RokuSeries
from plugins.Roku.shared import DETAILS_URL_REGEX, WATCH_URL_REGEX, RokuShared
from plugins.Roku.utils import is_movie
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class RokuInitializer(BasePluginInitializer, RokuShared): ...


# TODO: Validate
class Roku(RokuShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = RokuInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (DETAILS_URL_REGEX, WATCH_URL_REGEX)

    # TODO: Validate
    @override
    def get_media_importer(self, input: Show | str) -> RokuMedia:
        if isinstance(input, str):
            domain_regex = self._domain_regex()
            for url_regex in self._url_regexes():
                if match := re.match(domain_regex + url_regex, input):
                    # Every kind of content is answered at the same address, so
                    # the content has to be read before it is known which of them
                    # this one is.
                    key = match.group(1)
                    content_file = self.content_file(key)
                    self.raise_if_invalid_file(content_file, input)
                    content = content_file.parsed()
                    # A season or an episode belongs to a series, which is what
                    # is read and written.
                    if content.series is not None:
                        return RokuSeries(self)
                    if is_movie(content):
                        return RokuMovie(self)
                    return RokuSeries(self)

            msg = f"Invalid {self.plugin_name()} URL: {input}"
            raise InvalidURLError(msg)

        if not input.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        if input.media_type == "Movie":
            return RokuMovie(self)
        return RokuSeries(self)
