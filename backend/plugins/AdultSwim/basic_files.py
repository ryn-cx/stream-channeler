# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.AdultSwim.files import ShowPage, ShowsPage
from plugins.utils.base_plugin_v3.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def show_file(self, show_key: str) -> ShowPage:
        return self._file(ShowPage, show_key)

    # TODO: Validate
    def shows_file(self) -> ShowsPage:
        return self._file(ShowsPage)

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[ShowsPage]:
        return [self.shows_file()]
