# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Roku.files import content_id
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.Roku import Roku

# Movies, series and episodes use a plain content id, a season appends its number.
_CONTENT_ID_REGEX = r"[0-9a-f]{32}(?:-\d+)?"
_SLUG_REGEX = r"[^\/?#]+"


# TODO: Validate
class RokuURLHandler(URLHandler["Roku"]):
    # TODO: Validate
    def __init__(self, plugin: Roku, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        # A season or an episode URL is imported as the series it belongs to.
        if series := self.plugin.content_file(self._key).parsed().series:
            return content_id(series.meta.id)
        return self._key

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.content_file(self._key),
            self.url,
        )


# TODO: Validate
class DetailsURLHandler(RokuURLHandler):
    # https://therokuchannel.roku.com/details/db1607f1cff2522bb795382bb4b5bcae
    # https://therokuchannel.roku.com/details/db1607f1cff2522bb795382bb4b5bcae/fawlty-towers
    _URL_REGEX = (
        rf"\/details\/(?P<details_content_id>{_CONTENT_ID_REGEX})"
        rf"(?:\/{_SLUG_REGEX})?(?:\/|$)"
    )


# TODO: Validate
class WatchURLHandler(RokuURLHandler):
    # https://therokuchannel.roku.com/watch/db1607f1cff2522bb795382bb4b5bcae
    _URL_REGEX = rf"\/watch\/(?P<watch_content_id>{_CONTENT_ID_REGEX})(?:\/|$)"
