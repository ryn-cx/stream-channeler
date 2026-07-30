# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.NHKWorld import NHKWorld


class NHKWorldURLHandler(URLHandler["NHKWorld"]):
    def __init__(self, plugin: NHKWorld, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)


class ShowURLHandler(NHKWorldURLHandler):
    # https://www3.nhk.or.jp/nhkworld/en/shows/100years-midosuji/
    # The lookahead requires a non-numeric character so this matches show slugs but
    # not numeric episode URLs like https://www3.nhk.or.jp/nhkworld/en/shows/5001461/
    _PATH_REGEX = r"\/nhkworld\/en\/shows\/(?P<show_key>(?=[a-z0-9_-]*[a-z_-])[a-z0-9_-]+)\/?(?:$|[?#])"

    @property
    @override
    def show_key(self) -> str:
        return self._key

    @override
    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.video_program_file(self._key),
            self.url,
        )
