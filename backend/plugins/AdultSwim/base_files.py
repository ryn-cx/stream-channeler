# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.AdultSwim.files import TitlePage, TitlesPage
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO: Validate
class AdultSwimBaseFiles(BasePlugin):
    # TODO: Validate
    def title_file(self, title_key: str) -> TitlePage:
        return self._file(TitlePage, title_key)

    # TODO: Validate
    def titles_file(self) -> TitlesPage:
        return self._file(TitlesPage)

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[TitlesPage]:
        return [self.titles_file()]
