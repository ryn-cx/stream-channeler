# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.HiDive.base import HiDiveBase
from plugins.utils.base_plugin_v2.initialize import PluginInitializer


# TODO: Validate
class HiDiveInitializer(PluginInitializer, HiDiveBase):
    # TODO: Validate
    @override
    def initialize_channels(self) -> None:
        self._schedule_channel()
        self._process_new_schedule_files(self._sources[self.plugin_name()])
