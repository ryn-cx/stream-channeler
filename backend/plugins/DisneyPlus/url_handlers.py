# TODO: Validate
"""Disney+ URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.DisneyPlus import DisneyPlus


# TODO: Validate
class DisneyPlusURLHandler(URLHandler["DisneyPlus"]):
    """What every Disney+ URL has in common."""

    # TODO: Validate
    def __init__(self, plugin: DisneyPlus, url: str, key: str) -> None:
        """Initialize the URL handler."""
        self._key = key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key


# TODO: Validate
class EntityURLHandler(DisneyPlusURLHandler):
    """Disney+ title URL handler.

    Example URL https://www.disneyplus.com/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
    Example URL https://www.disneyplus.com/en-gb/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
    """

    # The optional locale segment, e.g. /en-gb or /de.
    _URL_REGEX = (
        r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?\/browse\/entity-"
        r"(?P<entity_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
        r"(?:\/|$)"
    )

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.entity_file(self._key),
            self.url,
        )
