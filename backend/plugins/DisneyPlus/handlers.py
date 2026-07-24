# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.DisneyPlus import DisneyPlus

_UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# Optional locale segment, e.g. /en-gb or /de.
_LOCALE_REGEX = r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?"


class DisneyPlusURLHandler(URLHandler["DisneyPlus"]):
    def __init__(self, plugin: DisneyPlus, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    @property
    def show_key(self) -> str:
        return self._key


class EntityURLHandler(DisneyPlusURLHandler):
    # https://www.disneyplus.com/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
    # https://www.disneyplus.com/en-gb/browse/entity-3135b0cb-a002-438d-a9fd-60d86284c93f
    _PATH_REGEX = (
        rf"{_LOCALE_REGEX}\/browse\/entity-(?P<entity_id>{_UUID_REGEX})(?:\/|$)"
    )

    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.entity_file(self._key),
            self.url,
        )
