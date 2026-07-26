# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.Amazon import Amazon

_ASIN_REGEX = r"[A-Z0-9]{10}"


class AmazonURLHandler(URLHandler["Amazon"]):
    def __init__(self, plugin: Amazon, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    @property
    def show_key(self) -> str:
        return self._key


class DetailURLHandler(AmazonURLHandler):
    # https://www.amazon.com/dp/B095RHJ52R
    # https://www.amazon.com/gp/video/detail/B095RHJ52R
    _PATH_REGEX = rf"\/(?:dp|gp\/video\/detail)\/(?P<asin>{_ASIN_REGEX})"

    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.detail_page(self._key),
            self.url,
        )
