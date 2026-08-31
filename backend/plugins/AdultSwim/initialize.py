# TODO: Validate
from __future__ import annotations

from typing import override

from app.utils import tz_datetime
from plugins.AdultSwim.base import AdultSwimBase
from plugins.utils.base_plugin_v2.initialize import PluginInitializer


# TODO: Validate
class AdultSwimInitializer(PluginInitializer, AdultSwimBase):
    # TODO: Validate
    @override
    def _initialize_sources(self) -> None:
        super()._initialize_sources()
        if self.plugin.update_at is None:
            self.plugin.update_at = tz_datetime.now()

    # TODO: Validate
    @override
    def _initialize_channels(self) -> None:
        self._channels()
        self._process_new_shows()
