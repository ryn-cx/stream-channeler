# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.DisneyPlus.shared import DisneyPlusShared
from plugins.utils.base_plugin.updater import BasePluginUpdater


# TODO: Validate
class DisneyPlusUpdater(DisneyPlusShared, BasePluginUpdater):
    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return []
