# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Roku.constants import DETAILS_URL_REGEX, WATCH_URL_REGEX
from plugins.Roku.importer import RokuImporter, RokuMovieImporter, RokuSeriesImporter
from plugins.Roku.shared import RokuShared
from plugins.Roku.utils import is_movie
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class Roku(RokuShared, AbstractPlugin, register=False):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (DETAILS_URL_REGEX, WATCH_URL_REGEX)

    # TODO: Validate
    def _url_content_key(self, url: str) -> str:
        domain_regex = self._domains_regex()
        for url_regex in self._url_regexes():
            if match := re.match(domain_regex + url_regex, url):
                return match.group(1)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> RokuImporter:
        content_file = self.content_file(self._url_content_key(url))
        self.raise_invalid_url_if_no_content(content_file, url)
        content = content_file.parsed()
        # A season or an episode belongs to a series, which is what
        # is read and written.
        if content.series is not None:
            return RokuSeriesImporter(self.session, self.plugin, self._file_cache)
        if is_movie(content):
            return RokuMovieImporter(self.session, self.plugin, self._file_cache)
        return RokuSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> RokuImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return RokuMovieImporter(self.session, self.plugin, self._file_cache)
        return RokuSeriesImporter(self.session, self.plugin, self._file_cache)
