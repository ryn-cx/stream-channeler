# TODO: Validate
"""Amazon Prime Video URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Amazon.keys import TITLE_KEY_REGEX
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.Amazon import Amazon

_TITLE_KEY_REGEX = TITLE_KEY_REGEX

# The id Amazon writes into a share link, which names the title in a different
# id space to the one its own pages are keyed by.
_GTI_REGEX = r"amzn1\.dv\.gti\.[0-9a-f-]+"


# TODO: Validate
class AmazonURLHandler(URLHandler["Amazon"]):
    """What every Amazon URL has in common."""

    # TODO: Validate
    def __init__(self, plugin: Amazon, url: str, key: str) -> None:
        """Initialize the URL handler."""
        self._key = key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self.plugin.show_key_from_title_key(self._key)

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        detail_file = self.plugin.detail_file(self._key)
        self.plugin.raise_if_invalid_file(detail_file, self.url)
        if message := detail_file.unavailable_message():
            msg = f"{message}: {self.url}"
            raise InvalidURLError(msg)


# TODO: Validate
class PrimeVideoDetailURLHandler(AmazonURLHandler):
    """Prime Video title URL handler.

    Example URL https://www.primevideo.com/detail/0GTKUFQSFLP1YVFDMW9IR56I90
    """

    # The region a link was written in is the region of whoever wrote it, and the
    # title is the same title whichever region asked for it.
    _URL_REGEX = rf"(?:\/region\/[a-z]{{2}})?\/detail\/(?P<prime_video_title_key>{_TITLE_KEY_REGEX})"


# TODO: Validate
class AmazonDetailURLHandler(AmazonURLHandler):
    """Amazon title URL handler.

    Example URL https://www.amazon.com/gp/video/detail/B0D9MYVLNM
    """

    # The title slug Amazon puts in front of /dp/ is decorative, only the id
    # after it matters.
    _URL_REGEX = rf"(?:\/[^\/]+)?\/(?:dp|gp\/video\/detail)\/(?P<amazon_title_key>{_TITLE_KEY_REGEX})"


# TODO: Validate
class RedirectURLHandler(AmazonURLHandler):
    """A link that names a title Amazon only answers for with a redirect.

    Amazon writes a share link with an id of its own that none of Prime Video's
    pages are keyed by, and answers it by pointing at the page that is. The id
    is therefore read off where the link lands rather than out of the link, so
    the rest of the plugin is handed the same kind of id every other URL gives.
    """

    # TODO: Validate
    @override
    def __init__(self, plugin: Amazon, url: str, key: str) -> None:
        """Initialize the URL handler, keyed by the title the link points at."""
        super().__init__(plugin, url, plugin.title_key_from_share_key(key))


# TODO: Validate
class WatchAmazonDetailURLHandler(RedirectURLHandler):
    """Amazon share link URL handler.

    Example URL
    https://watch.amazon.com/detail?gti=amzn1.dv.gti.92ad2133-d35e-1cb1-5d8e-f7b122a68228
    """

    _URL_REGEX = rf"\/detail\?gti=(?P<watch_amazon_title_key>{_GTI_REGEX})"
