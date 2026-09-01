# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.NHKWorld.base import NHKWorldBase
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin_v2.importer import BaseImporter


# TODO: Validate
class NHKWorldImporter(BaseImporter, NHKWorldBase):
    # https://www3.nhk.or.jp/nhkworld/en/shows/100years-midosuji/
    # The lookahead requires a non-numeric character so this matches show slugs but
    # not numeric episode URLs like https://www3.nhk.or.jp/nhkworld/en/shows/5001461/
    _SHOW_URL_REGEX = r"\/nhkworld\/en\/shows\/(?P<show_key>(?=[a-z0-9_-]*[a-z_-])[a-z0-9_-]+)\/?(?:$|[?#])"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._SHOW_URL_REGEX,)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._SHOW_URL_REGEX, url):
            show_key = match.group("show_key")
            self.raise_if_invalid_file(self.video_program_file(show_key), url)
            return show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
