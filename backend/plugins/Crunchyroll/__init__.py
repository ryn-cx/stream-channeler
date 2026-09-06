# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.sources.models import Source
from plugins.Crunchyroll.importer import (
    CrunchyrollAnimeImporter,
    CrunchyrollImporter,
    CrunchyRollMusicImporter,
)
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.utils import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    EPISODE_URL_REGEX,
    MUSIC_SOURCE,
    MUSIC_VIDEO_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_SOURCE,
)
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.media.media_type import TMDBMediaType
    from app.titles.models import Title


# TODO: Validate
class CrunchyrollInitializer(BasePluginInitializer, CrunchyrollShared):
    @override
    def _create_source_records(self) -> None:
        # Default implementation calls self.upsert_source (Crunchyroll.upsert_source)
        # which would then call self.browse_file() (Crunchyroll.browse_file) which does
        # not work because .browse_file() has a different implementation in
        # CrunchyrollSeries and CrunchyrollArtist.
        if Source.get(self.session, self.plugin, VIDEO_SOURCE) is None:
            CrunchyrollAnimeImporter(self).upsert_source(VIDEO_SOURCE)
        if Source.get(self.session, self.plugin, MUSIC_SOURCE) is None:
            CrunchyRollMusicImporter(self).upsert_source(MUSIC_SOURCE)
        self._sources = {source.key: source for source in self.plugin.sources}

    @override
    def _create_channel_records(self) -> None:
        CrunchyrollAnimeImporter(self).create_channel_records()
        CrunchyRollMusicImporter(self).create_channel_records()


# TODO: Validate
class Crunchyroll(
    WatchHistoryMixin,
    CrunchyrollShared,
    BaseReadURL,
    AbstractPlugin,
    register=False,
):
    initializer = CrunchyrollInitializer

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            MUSIC_VIDEO_URL_REGEX,  # Must be listed first due to URL overlap.
            CONCERT_URL_REGEX,
            ARTIST_URL_REGEX,
            SERIES_URL_REGEX,
            EPISODE_URL_REGEX,
        )

    @override
    def _get_media_importer_from_url(self, url: str) -> CrunchyrollImporter:
        domain_regex = self._domain_regex()
        for url_regex in (MUSIC_VIDEO_URL_REGEX, CONCERT_URL_REGEX, ARTIST_URL_REGEX):
            if re.match(domain_regex + url_regex, url):
                return CrunchyRollMusicImporter(self)
        for url_regex in (SERIES_URL_REGEX, EPISODE_URL_REGEX):
            if re.match(domain_regex + url_regex, url):
                return CrunchyrollAnimeImporter(self)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def _get_media_importer_from_title(self, title: Title) -> CrunchyrollImporter:
        return self.get_media_importer_from_source(title.source)

    @override
    def get_media_importer_from_source(self, source: Source) -> CrunchyrollImporter:
        if source.key == MUSIC_SOURCE:
            return CrunchyRollMusicImporter(self)
        return CrunchyrollAnimeImporter(self)

    @override
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        for datum in self.search_file(names[0]).parsed().data:
            for item in datum.items:
                # Series doesn't actually differentiate between movies and series as all
                # movies are also labeled as series here.
                if item.type == "series":
                    # search_for_url is used for TMDB cross-referencing so music entries
                    # are ignored because TMDB does not have music entries.
                    return CrunchyrollAnimeImporter.title_url(item.id)
        return None
