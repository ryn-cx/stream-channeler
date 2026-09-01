# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.DisneyPlus.base import DisneyPlusBase
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin_v2.importer import BaseImporter


# TODO: Validate
class DisneyPlusImporter(BaseImporter, DisneyPlusBase):
    # https://www.disneyplus.com/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
    # https://www.disneyplus.com/en-gb/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
    # The optional locale segment, e.g. /en-gb or /de.
    _ENTITY_URL_REGEX = (
        r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?\/browse\/entity-"
        r"(?P<entity_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
        r"(?:\/|$)"
    )

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._ENTITY_URL_REGEX,)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._ENTITY_URL_REGEX, url):
            show_key = match.group("entity_id")
            self.raise_if_invalid_file(self.entity_file(show_key), url)
            return show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
