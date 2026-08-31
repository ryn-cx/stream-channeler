# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.Amazon.constants import TITLE_KEY_REGEX
from plugins.Amazon.utils import HelperMixin
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.plugin import ReadURLPlugin


# TODO: Validate
class ImportURLMixin(HelperMixin, ReadURLPlugin, register=False):
    # https://watch.amazon.com/detail?gti=amzn1.dv.gti.92ad2133-d35e-1cb1-5d8e-f7b122a68228
    # The id Amazon writes into a share link, which names the title in a
    # different id space to the one its own pages are keyed by.
    _SHARE_URL_REGEX = (
        r"\/detail\?gti=(?P<watch_amazon_title_key>amzn1\.dv\.gti\.[0-9a-f-]+)"
    )
    # https://www.primevideo.com/detail/0GTKUFQSFLP1YVFDMW9IR56I90
    # The region a link was written in is the region of whoever wrote it, and the
    # title is the same title whichever region asked for it.
    _PRIME_VIDEO_URL_REGEX = rf"(?:\/region\/[a-z]{{2}})?\/detail\/(?P<prime_video_title_key>{TITLE_KEY_REGEX})"
    # https://www.amazon.com/gp/video/detail/B0D9MYVLNM
    # The title slug Amazon puts in front of /dp/ is decorative, only the id
    # after it matters.
    _AMAZON_URL_REGEX = rf"(?:\/[^\/]+)?\/(?:dp|gp\/video\/detail)\/(?P<amazon_title_key>{TITLE_KEY_REGEX})"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            # Must be listed first: a share link's path is also a detail path, and
            # only this one carries the id in the query rather than the path.
            cls._SHARE_URL_REGEX,
            cls._PRIME_VIDEO_URL_REGEX,
            cls._AMAZON_URL_REGEX,
        )

    # TODO: Validate
    @override
    def _read_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        title_key: str | None
        if match := re.match(domain_regex + self._SHARE_URL_REGEX, url):
            # Amazon answers a share link by pointing at the page its own ids key,
            # so the id is read off where the link lands rather than out of the link.
            title_key = self.title_key_from_share_key(
                match.group("watch_amazon_title_key"),
            )
        elif match := re.match(domain_regex + self._PRIME_VIDEO_URL_REGEX, url):
            title_key = match.group("prime_video_title_key")
        elif match := re.match(domain_regex + self._AMAZON_URL_REGEX, url):
            title_key = match.group("amazon_title_key")
        else:
            title_key = None

        if title_key is None:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)

        detail_file = self.detail_file(title_key)
        self.raise_if_invalid_file(detail_file, url)
        if message := detail_file.unavailable_message():
            msg = f"{message}: {url}"
            raise InvalidURLError(msg)

        self._show_key = self.show_key_from_title_key(title_key)
