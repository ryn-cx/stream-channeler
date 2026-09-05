# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Amazon.media import AmazonMedia, AmazonMovie, AmazonSeries
from plugins.Amazon.shared import (
    AMAZON_URL_REGEX,
    PRIME_VIDEO_URL_REGEX,
    SHARE_URL_REGEX,
    AmazonShared,
)
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin_v3.base import BaseReadURL
from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class AmazonInitializer(BasePluginInitializer, AmazonShared): ...


# TODO: Validate
class Amazon(AmazonShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = AmazonInitializer

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
    @override
    def get_media_importer(self, input: Show | str) -> AmazonMedia:
        if isinstance(input, str):
            # A film and a season of a series are answered at the same address,
            # so the page has to be read before it is known which of the two it
            # is.
            title_key = self._url_title_key(input)
            self.raise_if_invalid_file(self.detail_file(title_key), input)
            if self._is_movie(title_key):
                return AmazonMovie(self)
            return AmazonSeries(self)

        if not input.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        if input.media_type == "Movie":
            return AmazonMovie(self)
        return AmazonSeries(self)

    # TODO: Validate
    def _url_title_key(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SHARE_URL_REGEX, url):
            return self.title_key_from_share_key(
                match.group("watch_amazon_title_key"),
            )
        if match := re.match(domain_regex + PRIME_VIDEO_URL_REGEX, url):
            return match.group("prime_video_title_key")
        if match := re.match(domain_regex + AMAZON_URL_REGEX, url):
            return match.group("amazon_title_key")

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
