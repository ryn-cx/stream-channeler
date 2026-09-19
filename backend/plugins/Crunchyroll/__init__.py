# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.sources.models import Source
from plugins.Crunchyroll.anime_importer import CrunchyrollAnimeImporter
from plugins.Crunchyroll.constants import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    EPISODE_URL_REGEX,
    MUSIC_SOURCE,
    MUSIC_VIDEO_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_SOURCE,
)
from plugins.Crunchyroll.music_importer import CrunchyrollMusicImporter
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.watch_history import CrunchyrollWatchHistoryMixin
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime

    from app.titles.models import Title


# TODO: Validate
class Crunchyroll(
    CrunchyrollWatchHistoryMixin,
    CrunchyrollShared,
    AbstractPlugin,
    register=True,
):
    VIDEO_STORE_IMAGES = False
    VIDEO_STORE_SCORE = False
    VIDEO_STORE_POPULARITY = False

    @override
    def create_initial_source_records(self) -> None:
        # CrunchyrollAnimeImporter and CrunchyrollMusicImporter need to be initialized
        # to support calls to _source_files inside of upsert_source.
        CrunchyrollAnimeImporter(
            self.session,
            self.plugin,
            self._file_cache,
        ).upsert_source(VIDEO_SOURCE)
        CrunchyrollMusicImporter(
            self.session,
            self.plugin,
            self._file_cache,
        ).upsert_source(MUSIC_SOURCE)

    @override
    def create_initial_channel_records(self) -> None:
        CrunchyrollAnimeImporter(
            self.session,
            self.plugin,
            self._file_cache,
        ).create_initial_channel_records()
        CrunchyrollMusicImporter(
            self.session,
            self.plugin,
            self._file_cache,
        ).create_initial_channel_records()

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            MUSIC_VIDEO_URL_REGEX,  # Must be listed first due to regex overlap.
            CONCERT_URL_REGEX,
            ARTIST_URL_REGEX,
            SERIES_URL_REGEX,
            EPISODE_URL_REGEX,
        )

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
        return self._media_importer_from_title(title).similar_title_urls(title)

    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        if source.key == MUSIC_SOURCE:
            CrunchyrollMusicImporter(
                self.session,
                self.plugin,
                self._file_cache,
            ).update_source(source, update_at)
        else:
            CrunchyrollAnimeImporter(
                self.session,
                self.plugin,
                self._file_cache,
            ).update_source(source, update_at)
