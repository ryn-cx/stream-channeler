# TODO: Validate
"""What the plugin, its importers and its initializer all read Prime Video by."""

from __future__ import annotations

import re
from typing import override

from plugins.Amazon.base_files import AmazonBaseFiles
from plugins.Amazon.constants import (
    AMAZON_URL_REGEX,
    PRIME_VIDEO_URL_REGEX,
)
from plugins.utils.abstract_plugin import InvalidURLError


# TODO: Validate
class AmazonShared(AmazonBaseFiles):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Amazon"

    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        # This is just the names that do not fall under the "XXX Amazon Channel" format,
        # those names are checked in matches_tmdb_provider.
        return ("Amazon Prime Video", "Amazon Video", "Prime Video")

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.primevideo.com/favicon.ico"

    @classmethod
    @override
    def _domains(cls) -> list[str]:
        return ["primevideo.com", "amazon.com"]

    @classmethod
    @override
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        if super().matches_tmdb_provider(provider_name):
            return True
        return provider_name.endswith("Amazon Channel")

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (PRIME_VIDEO_URL_REGEX, AMAZON_URL_REGEX)

    # TODO: Validate
    def link_id_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        for url_regex in (PRIME_VIDEO_URL_REGEX, AMAZON_URL_REGEX):
            if match := re.match(domain_regex + url_regex, url):
                return match.group("link_id")

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def title_key_from_url(self, url: str) -> str:
        # link_id is the id inside of the URL, this URL may point to a season so it
        # needs to be downloaded and parsed to get the actual title key.
        link_id = self.link_id_from_url(url)
        detail_file = self.detail_file(link_id)
        if detail_file.does_not_exist():
            detail_file.download_if_outdated()
        return detail_file.parsed().title_key
