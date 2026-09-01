# TODO: Validate
"""The records Hulu is given before anything is imported into it."""

from __future__ import annotations

from typing import override

from plugins.Hulu.base import HuluBase
from plugins.utils.base_plugin_v2.initialize import BasePluginInitializer


# TODO: Validate
class HuluInitializer(BasePluginInitializer, HuluBase):
    # TODO: Validate
    @override
    def _initialize_sources(self) -> None:
        self.genres_page_file().download_if_outdated()
        self._download_outdated_files(self._source_files())
        super()._initialize_sources()

    # TODO: Validate
    @override
    def _initialize_channels(self) -> None:
        self.add_media_to_plugin_channels()
