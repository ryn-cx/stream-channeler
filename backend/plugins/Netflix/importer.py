# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.Netflix.base import NetflixBase
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin_v2.importer import BaseImporter


# TODO: Validate
class NetflixImporter(BaseImporter, NetflixBase):
    # https://www.netflix.com/title/80240027
    _TITLE_URL_REGEX = r"\/title\/(?P<title_key>\d+)(?:\/|$)"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._TITLE_URL_REGEX, url):
            show_key = match.group("title_key")
            self.raise_if_invalid_file(self.title_file(show_key), url)
            return show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
