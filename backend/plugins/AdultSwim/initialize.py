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
    def initialize_sources(self) -> None:
        super().initialize_sources()
        if self.plugin.update_at is None:
            self.plugin.update_at = tz_datetime.now()
