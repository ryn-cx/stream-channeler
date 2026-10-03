# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Tubi.constants import TITLE_SITEMAP_REGEX
from plugins.Tubi.files import SitemapFile, SitemapIndexFile
from plugins.Tubi.shared import TubiShared
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Sequence


# TODO: Validate
class TubiUpdater(TubiShared, BasePluginUpdater):
    # TODO: Validate
    def sitemap_index_file(self) -> SitemapIndexFile:
        return self._cached_file(SitemapIndexFile)

    # TODO: Validate
    def sitemap_file(self, sitemap_name: str) -> SitemapFile:
        return self._cached_file(SitemapFile, sitemap_name)

    # TODO: Validate
    def title_sitemap_files(self) -> list[SitemapFile]:
        self.sitemap_index_file().download_if_outdated()
        return [
            self.sitemap_file(sitemap_name)
            for sitemap_name in self.sitemap_index_file().parsed()
            if re.match(TITLE_SITEMAP_REGEX, sitemap_name)
        ]

    # TODO: Validate
    @override
    def _plugin_files(self) -> Sequence[SitemapIndexFile | SitemapFile]:
        return [self.sitemap_index_file(), *self.title_sitemap_files()]

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        urls: dict[str, None] = {}
        for sitemap_file in self.title_sitemap_files():
            for url in sitemap_file.parsed():
                urls[url] = None
        return list(urls)

    # TODO: Validate
    @override
    def _title_keys_from_plugin_files(self) -> set[str]:
        return {self.title_key_from_url(url) for url in self._title_urls_from_files()}
