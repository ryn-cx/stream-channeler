# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.Amazon import Amazon

# A plain ASIN is 10 characters, but a deep link uses a longer encrypted title id.
_ASIN_REGEX = r"[A-Z0-9]{10,}"


# TODO: Validate
class AmazonURLHandler(URLHandler["Amazon"]):
    # TODO: Validate
    def __init__(self, plugin: Amazon, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key


# TODO: Validate
class DetailURLHandler(AmazonURLHandler):
    # https://www.amazon.com/dp/B095RHJ52R
    # https://www.amazon.com/gp/video/detail/B095RHJ52R
    # https://www.amazon.com/gp/video/detail/0GK0W5DZFOWP14GMAR51GE1AYD
    # https://www.amazon.com/Justice-League-Unlimited-Season-1/dp/B003LJVNEY
    # The title slug Amazon puts in front of /dp/ is decorative, only the ASIN matters.
    _URL_REGEX = rf"(?:\/[^\/]+)?\/(?:dp|gp\/video\/detail)\/(?P<asin>{_ASIN_REGEX})"

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.detail_page(self._key),
            self.url,
        )
