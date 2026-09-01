# TODO: Validate
"""The records Hulu is given before anything is imported into it."""

from __future__ import annotations

from typing import override

from plugins.Hulu.base import HuluBase
from plugins.utils.base_plugin_v2.initialize import PluginInitializer


# TODO: Validate
class HuluInitializer(PluginInitializer, HuluBase):
    # TODO: Validate
    @override
    def _initialize_channels(self) -> None:
        self.add_media_to_plugin_channels()
