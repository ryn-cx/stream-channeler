# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.HBOMax.shared import HBOMaxShared
from plugins.utils.base_plugin.updater import BasePluginUpdater


# TODO: Validate
class HBOMaxUpdater(HBOMaxShared, BasePluginUpdater):
    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return []
