# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.HBOMax.constants import SLUG_REGEX, UUID_REGEX
from plugins.HBOMax.utils import HelperMixin
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaTypeReadURLPlugin


# TODO: Validate
class ImportURLMixin(HelperMixin, MediaTypeReadURLPlugin, register=False):
    # The title slug HBO Max puts in front of the id is decorative, such as in
    # https://www.hbomax.com/movies/the-batman/4ee4f57e-19bd-493f-96f9-ad3e753af981
    _MOVIE_URL_REGEX = rf"\/movies?\/{SLUG_REGEX}(?P<movie_id>{UUID_REGEX})"
    # Any non-movie media-type prefix maps to a series, such as mini-series in
    # https://play.hbomax.com/mini-series/396999a6-3fff-4af3-802b-10c46d10deff
    # or shows in
    # https://www.hbomax.com/shows/rick-and-morty/s2/ab553cdc-e15d-4597-b65f-bec9201fd2dd
    # The media-type path segment is any of them, e.g. show, shows, mini-series,
    # limited-series.
    _SHOW_URL_REGEX = rf"\/[a-z-]+\/{SLUG_REGEX}(?:s\d+\/)?(?P<show_id>{UUID_REGEX})"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._MOVIE_URL_REGEX, cls._SHOW_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            self._show_key = match.group("movie_id")
            self._media_type = "movie"
            self.raise_if_invalid_file(self.movie_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._SHOW_URL_REGEX, url):
            self._show_key = match.group("show_id")
            self._media_type = "series"
            self.raise_if_invalid_file(self.show_file(self._show_key), url)
            return

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)
