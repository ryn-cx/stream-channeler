# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Roku.constants import DETAILS_URL_REGEX, WATCH_URL_REGEX
from plugins.Roku.importer import RokuImporter, RokuMovieImporter, RokuSeriesImporter
from plugins.Roku.shared import RokuShared
from plugins.Roku.utils import is_movie
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


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
    def _validate_url(self, url: str) -> None:
        content_file = self.content_file(self._url_content_key(url))
        self.raise_invalid_url_if_no_content(content_file, url)

    # TODO: Validate
    def _url_content_key(self, url: str) -> str:
        domain_regex = self._domain_regex()
        for url_regex in self._url_regexes():
            if match := re.match(domain_regex + url_regex, url):
                return match.group(1)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> RokuImporter:
        # Every kind of content is answered at the same address, so
        # the content has to be read before it is known which of them
        # this one is.
        content = self.content_file(self._url_content_key(url)).parsed()
        # A season or an episode belongs to a series, which is what
        # is read and written.
        if content.series is not None:
            return RokuSeriesImporter(self)
        if is_movie(content):
            return RokuMovieImporter(self)
        return RokuSeriesImporter(self)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> RokuImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return RokuMovieImporter(self)
        return RokuSeriesImporter(self)
