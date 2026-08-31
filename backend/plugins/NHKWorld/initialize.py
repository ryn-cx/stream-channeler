# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.NHKWorld.base import NHKWorldBase
from plugins.utils.base_plugin_v2.initialize import PluginInitializer


# TODO: Validate
class NHKWorldInitializer(PluginInitializer, NHKWorldBase):
    # TODO: Validate
    @override
    def initialize_channels(self) -> None:
        self._feed_channel()
        self._process_new_episodes_files(self._sources[self.plugin_name()])
