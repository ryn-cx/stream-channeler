from __future__ import annotations

from plugins.Amazon.files import Detail, DetailWidgets
from plugins.utils.base_plugin.base import BasePlugin


class AmazonBaseFiles(BasePlugin):
    def detail_file(self, link_id: str) -> Detail:
        return self._cached_file(Detail, link_id)

    def detail_widgets_file(self, season_key: str, page_index: int) -> DetailWidgets:
        return self._cached_file(DetailWidgets, season_key, page_index)
