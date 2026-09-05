# TODO: Validate
"""Crunchyroll plugin.

Detects new media much faster than JustWatch and supports music.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

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
    artist_url,
    episode_is_music,
    episode_url,
    series_url,
    show_is_an_artist,
)
from plugins.Crunchyroll.watch_history import WatchHistoryMixin
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin_v3.base import BaseReadURL
from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from datetime import datetime

    from chirashi.search.models import Item as SearchItem

    from app.media.media_type import TMDBMediaType
    from app.shows.models import Show
    from app.sources.models import Source


# TODO: Validate
class CrunchyrollInitializer(BasePluginInitializer, CrunchyrollShared):
    # TODO: Validate
    @override
    def _create_channel_records(self) -> None:
        # These functions shouldn't be inlined because they are the same
        # functions used for source updates.
        self.process_new_browse_files()
        self.process_new_music_browse_files()
        self.add_series_to_plugin_channels()
        self.add_music_to_plugin_channels()


# TODO: Validate
class Crunchyroll(
    WatchHistoryMixin,
    CrunchyrollShared,
    BaseReadURL,
    AbstractPlugin,
    register=False,
):
    """Crunchyroll plugin.

    Detects new media much faster than JustWatch and supports music.
    """

    initializer = CrunchyrollInitializer

    # TODO: Validate
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

    # TODO: Validate
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

        if show_is_an_artist(input.key):
            return CrunchyrollArtist(self)
        return CrunchyrollSeries(self)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        if source.key == MUSIC_SOURCE:
            self.update_music_source()
        else:
            self.update_video_source(source)

    # TODO: Validate
    @override
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        for datum in self.search_file(names[0]).parsed().data:
            for item in datum.items:
                return self._search_result_url(item)
        return None

    # TODO: Validate
    @staticmethod
    def _search_result_url(item: SearchItem) -> str:
        item_key = item.id
        if show_is_an_artist(item_key):
            return artist_url(item_key)
        if episode_is_music(item_key) or item.type == "episode":
            return episode_url(item_key)
        return series_url(item_key)
