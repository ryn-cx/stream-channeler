# TODO: Validate
"""Netflix URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.Netflix import Netflix


# TODO: Validate
class NetflixURLHandler(URLHandler["Netflix"]):
    """What every Netflix URL has in common."""

    # TODO: Validate
    def __init__(self, plugin: Netflix, url: str, key: str) -> None:
        """Initialize the URL handler."""
        self._key = key
        super().__init__(plugin, url)


# TODO: Validate
class TitleURLHandler(NetflixURLHandler):
    """Netflix title URL handler.

    Example URL https://www.netflix.com/title/80240027
    """

    _URL_REGEX = r"\/title\/(?P<title_key>\d+)(?:\/|$)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.title_file(self._key),
            self.url,
        )
