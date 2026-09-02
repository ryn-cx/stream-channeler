# TODO: Validate
from __future__ import annotations

from typing import override

from app.utils import tz_datetime
from plugins.AdultSwim.base import AdultSwimBase
from plugins.utils.base_plugin_v2.initialize import BasePluginInitializer


# TODO: Validate
class AdultSwimInitializer(BasePluginInitializer, AdultSwimBase):
    # TODO: Validate
    @override
    def _create_source_records(self) -> None:
        super()._create_source_records()
        if self.plugin.update_at is None:
            self.plugin.update_at = tz_datetime.now()

    # TODO: Validate
    @override
    def _create_channel_records(self) -> None:
        self._channels()
        self._process_new_shows()
