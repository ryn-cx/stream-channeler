from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.Netflix import Netflix


class NetflixURLHandler(URLHandler["Netflix"]):
    def __init__(self, plugin: Netflix, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)


class TitleURLHandler(NetflixURLHandler):
    # https://www.netflix.com/title/80240027
    _PATH_REGEX = r"\/title\/(?P<title_key>\d+)(?:\/|$)"

    @property
    @override
    def show_key(self) -> str:
        return self._key

    @override
    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.title_file(self._key),
            self.url,
        )
