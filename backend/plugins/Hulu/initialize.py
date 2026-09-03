from __future__ import annotations

from typing import override

from plugins.Hulu.base import HuluBase
from plugins.utils.base_plugin_v2.initialize import BasePluginInitializer


class HuluInitializer(BasePluginInitializer, HuluBase):
    # TODO: Validate
    @override
    def _create_source_records(self) -> None:
        # Predownload the first genre page file so the _source_files function does not
        # have to worry about making sure the genre page file exists.
        self.genres_page_file().download_if_outdated()
        _cache = self._preload_source_files()
        self._download_outdated_files(self._source_files())
        super()._create_source_records()

    @override
    def _create_channel_records(self) -> None:
        # This function shouldn't be inlined because it is the same function used for
        # source updates.
        self.add_media_to_plugin_channels()
