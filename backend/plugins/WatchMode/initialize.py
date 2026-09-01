# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.utils.base_plugin_v2.initialize import BasePluginInitializer
from plugins.WatchMode.base import WatchModeBase


# TODO: Validate
class WatchModeInitializer(BasePluginInitializer, WatchModeBase):
    # Watchmode holds no listing of its own, so it has no `Source` to create.
    # TODO: Validate
    @override
    def _initialize_sources(self) -> None:
        return
