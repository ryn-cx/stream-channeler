# TODO: Validate
"""Crunchyroll plugin.

Detects new media much faster than JustWatch and supports music.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.sources.models import Source
from plugins.Crunchyroll.media import (
    CrunchyrollArtist,
    CrunchyrollMedia,
    CrunchyrollSeries,
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
    series_url,
)
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.media.media_type import TMDBMediaType
    from app.shows.models import Show


class CrunchyrollInitializer(BasePluginInitializer, CrunchyrollShared):
    @override
    def _create_source_records(self) -> None:
        if Source.get(self.session, self.plugin, VIDEO_SOURCE) is None:
            CrunchyrollSeries(self).upsert_source(VIDEO_SOURCE)
        if Source.get(self.session, self.plugin, MUSIC_SOURCE) is None:
            CrunchyrollArtist(self).upsert_source(MUSIC_SOURCE)
        self._sources = {source.key: source for source in self.plugin.sources}

    @override
    def _create_channel_records(self) -> None:
        CrunchyrollSeries(self).create_channel_records()
        CrunchyrollArtist(self).create_channel_records()


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
    def get_media_importer(self, input: Show | str) -> CrunchyrollMedia:
        if isinstance(input, str):
            domain_regex = self._domain_regex()
            for url_regex in (
                MUSIC_VIDEO_URL_REGEX,
                CONCERT_URL_REGEX,
                ARTIST_URL_REGEX,
            ):
                if re.match(domain_regex + url_regex, input):
                    return CrunchyrollArtist(self)
            for url_regex in (SERIES_URL_REGEX, EPISODE_URL_REGEX):
                if re.match(domain_regex + url_regex, input):
                    return CrunchyrollSeries(self)

            msg = f"Invalid {self.plugin_name()} URL: {input}"
            raise InvalidURLError(msg)

        if input.key.startswith("MA"):  # MA might stand for Music Artist.
            return CrunchyrollArtist(self)
        return CrunchyrollSeries(self)

    # TODO: Validate
    @override
    def get_source_importer(self, source: Source) -> CrunchyrollMedia:
        if source.key == MUSIC_SOURCE:
            return CrunchyrollArtist(self)
        return CrunchyrollSeries(self)

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
                    return series_url(item.id)
        return None
