# TODO: Validate
"""What the plugin, its importers and its initializer all read Prime Video by."""

from __future__ import annotations

import re
from typing import override

from plugins.Amazon.base_files import AmazonBaseFiles
from plugins.Amazon.constants import (
    AMAZON_URL_REGEX,
    PRIME_VIDEO_URL_REGEX,
    SHARE_URL_REGEX,
)
from plugins.utils.abstract_plugin import InvalidURLError


# TODO: Validate
class AmazonShared(AmazonBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Amazon"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Amazon Prime Video", "Amazon Video", "Prime Video")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.primevideo.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domains(cls) -> list[str]:
        # Prime Video is read out of its own website, and Amazon's is listed as
        # well because a link to a title on it is a link to the same title.
        # watch.amazon.com is the domain Amazon writes a share link under, and
        # is its own entry because only an optional `www.` is read off a domain.
        return ["primevideo.com", "amazon.com", "watch.amazon.com"]

    # TODO: Validate
    @classmethod
    @override
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        if super().matches_tmdb_provider(provider_name):
            return True
        return provider_name.endswith("Amazon Channel")

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            # Must be listed first: a share link's path is also a detail path, and
            # only this one carries the id in the query rather than the path.
            SHARE_URL_REGEX,
            PRIME_VIDEO_URL_REGEX,
            AMAZON_URL_REGEX,
        )

    # TODO: Validate
    def _written_link_id_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        for url_regex in (PRIME_VIDEO_URL_REGEX, AMAZON_URL_REGEX):
            if match := re.match(domain_regex + url_regex, url):
                return match.group("link_id")

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def link_id_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SHARE_URL_REGEX, url):
            return self.share_link_file(match.group("link_id")).link_id()

        return self._written_link_id_from_url(url)

    # TODO: Validate
    def stored_link_id_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SHARE_URL_REGEX, url):
            share_id = match.group("link_id")
            share_link = self.share_link_file(share_id)
            if share_link.does_not_exist():
                return share_id
            return share_link.link_id()

        return self._written_link_id_from_url(url)

    # TODO: Validate
    @override
    def title_key_from_url(self, url: str) -> str:
        link_id = self.stored_link_id_from_url(url)
        detail_file = self.detail_file(link_id)
        if detail_file.does_not_exist():
            return link_id
        return detail_file.title_key()
