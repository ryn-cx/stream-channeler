# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.ParamountPlus.base import ParamountPlusBase
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin_v2.importer import BaseImporter


# TODO: Validate
class ParamountPlusImporter(BaseImporter, ParamountPlusBase):
    # https://www.paramountplus.com/movies/video/ALVE01KT235XQDEK58R7H2012VNZMK/
    _MOVIE_URL_REGEX = r"\/movies\/video\/(?P<movie_id>[A-Za-z0-9]+)(?:\/|$)"
    # https://www.paramountplus.com/shows/south-park/
    _SHOW_URL_REGEX = r"\/shows\/(?P<show_id>[a-z0-9-]+)(?:\/|$)"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._MOVIE_URL_REGEX, cls._SHOW_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            show_key = match.group("movie_id")
            self._media_type = "movie"
            self.raise_if_invalid_file(self.movie_file(show_key), url)
            return show_key

        if match := re.match(domain_regex + self._SHOW_URL_REGEX, url):
            show_key = match.group("show_id")
            self._media_type = "series"
            self.raise_if_invalid_file(self.show_page_file(show_key), url)
            return show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
