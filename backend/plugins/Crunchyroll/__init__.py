# TODO: Validate
from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, override
from urllib.parse import urlsplit

from app.titles.models import Title
from plugins.Crunchyroll.anime_importer import CrunchyrollAnimeImporter
from plugins.Crunchyroll.constants import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    MUSIC_SOURCE,
    MUSIC_VIDEO_URL_REGEX,
)
from plugins.Crunchyroll.linker import CrunchyrollLinker
from plugins.Crunchyroll.music_importer import CrunchyrollMusicImporter
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.updater import CrunchyrollUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.watch_history import BaseWatchHistoryDispatcherMixin
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from collections.abc import Collection


# TODO: Validate
class Crunchyroll(
    CrunchyrollShared,
    BaseMediaImporterMixin,
    BaseWatchHistoryDispatcherMixin,
    BasePlugin,
    register=True,
):
    CATALOG_SUPPORT = CatalogSupport.yes
    PROXY_IMAGES = True
    import_watch_history_file_extension = ".json"

    # TODO: Validate
    @staticmethod
    @override
    def image_file_name(url: str) -> str:
        path = PurePosixPath(urlsplit(url).path)
        extension = path.suffix.removeprefix(".")
        return f"{path.stem}.{'jpeg' if extension == 'jpg' else extension}"

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[CrunchyrollUpdater]:
        return CrunchyrollUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[CrunchyrollLinker]:
        return CrunchyrollLinker

    # TODO: Validate
    def _crunchyroll_updater(self) -> CrunchyrollUpdater:
        return CrunchyrollUpdater(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _watch_history_importer(self) -> CrunchyrollUpdater:
        return self._crunchyroll_updater()

    @override
    def _media_importer_from_url(
        self,
        url: str,
    ) -> CrunchyrollAnimeImporter | CrunchyrollMusicImporter:
        domain_regex = self._domains_regex()
        for url_regex in (MUSIC_VIDEO_URL_REGEX, CONCERT_URL_REGEX, ARTIST_URL_REGEX):
            if re.match(domain_regex + url_regex, url):
                return CrunchyrollMusicImporter(
                    self.session,
                    self.plugin,
                    self._file_cache,
                )
        return CrunchyrollAnimeImporter(self.session, self.plugin, self._file_cache)

    @override
    def _media_importer_from_title(
        self,
        title: Title,
    ) -> CrunchyrollAnimeImporter | CrunchyrollMusicImporter:
        if title.source.key == MUSIC_SOURCE:
            return CrunchyrollMusicImporter(self.session, self.plugin, self._file_cache)
        return CrunchyrollAnimeImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._crunchyroll_updater().similar_title_urls(title)
