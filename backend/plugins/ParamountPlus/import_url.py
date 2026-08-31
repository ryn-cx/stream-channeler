# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.ParamountPlus.utils import HelperMixin
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaTypeReadURLPlugin


# TODO: Validate
class ImportURLMixin(HelperMixin, MediaTypeReadURLPlugin, register=False):
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
    def _read_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            self._show_key = match.group("movie_id")
            self._media_type_value = "movie"
            self.raise_if_invalid_file(self.movie_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._SHOW_URL_REGEX, url):
            self._show_key = match.group("show_id")
            self._media_type_value = "series"
            self.raise_if_invalid_file(self.show_page_file(self._show_key), url)
            return

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)
