# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Roku.shared import RokuShared
from plugins.utils.base_plugin.updater import BasePluginUpdater


# TODO: Validate
class RokuUpdater(RokuShared, BasePluginUpdater):
    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return []
