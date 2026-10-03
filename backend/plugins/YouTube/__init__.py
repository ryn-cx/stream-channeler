# TODO: Validate

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport
from plugins.YouTube.importer import YouTubeImporter
from plugins.YouTube.linker import YouTubeLinker
from plugins.YouTube.music_importer import YouTubeMusicImporter
from plugins.YouTube.shared import YouTubeShared
from plugins.YouTube.updater import YouTubeUpdater
from plugins.YouTube.url_parser import YouTubeURLParserMixin

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.channels.models import ChannelQueue
    from app.seasons.models import Season
    from app.titles.models import Title


# TODO: Validate
class YouTube(
    YouTubeURLParserMixin,
    YouTubeShared,
    BaseMediaImporterMixin,
    BasePlugin,
    register=True,
):
    CATALOG_SUPPORT = CatalogSupport.no
    KNOWN_ISSUES = "Limited to 10,000 API requests per day."

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[YouTubeUpdater]:
        return YouTubeUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[YouTubeLinker]:
        return YouTubeLinker

    # TODO: Validate
    def _youtube_updater(self) -> YouTubeUpdater:
        return YouTubeUpdater(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @classmethod
    @override
    def specialized_updater(cls) -> bool:
        return True

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> YouTubeImporter:
        if title.media_type == MediaType.youtube_artist:
            return YouTubeMusicImporter(self.session, self.plugin, self._file_cache)
        return self.media_importer_from_title_key(title.key)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> YouTubeImporter:
        parsed = self._parsed_url(url)
        if parsed.album_playlist_key:
            importer: YouTubeImporter = YouTubeMusicImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        else:
            importer = self.media_importer_from_title_key(parsed.title_key)
        importer.parsed_url = parsed
        return importer

    # TODO: Validate
    def download_missing_videos(self, video_keys: Iterable[str]) -> None:
        self._youtube_updater().download_missing_videos(video_keys)

    # TODO: Validate
    def playlist_season_episode_keys(self, season: Season) -> list[str]:
        return self._media_importer_from_title(
            season.title,
        ).playlist_season_episode_keys(season)

    # TODO: Validate
    def update_playlist_season(self, season: Season) -> None:
        self._media_importer_from_title(season.title).update_playlist_season(season)

    # TODO: Validate
    @override
    def on_import_url_failure(
        self,
        queue_item: ChannelQueue,
        error: Exception,
    ) -> None:
        self._youtube_updater().on_import_url_failure(queue_item, error)
