# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.IMDb.shared import IMDbShared
from plugins.utils.base_plugin.updater import BasePluginUpdater


# TODO: Validate
class IMDbUpdater(IMDbShared, BasePluginUpdater):
    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return ()

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return []
