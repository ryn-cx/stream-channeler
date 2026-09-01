# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.NHKWorld.base import NHKWorldBase
from plugins.utils.base_plugin_v2.initialize import BasePluginInitializer


# TODO: Validate
class NHKWorldInitializer(BasePluginInitializer, NHKWorldBase):
    # TODO: Validate
    @override
    def _initialize_channels(self) -> None:
        self._feed_channel()
        self._process_new_episodes_files(self._sources[self.plugin_name()])
