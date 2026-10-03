# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Netflix.files import LodpTitleAndPlansPage
from plugins.Netflix.shared import NetflixShared
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class NetflixUpdater(NetflixShared, BasePluginUpdater):
    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return []

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:
        similar_file = self.similar_file(title.key)
        # TODO: This is temporary until all files are downloaded
        similar_file.download_if_outdated()
        return [
            self.title_url(str(similar.video_id))
            for similar in similar_file.parsed().similar_videos
        ]

    def similar_file(self, title_key: str) -> LodpTitleAndPlansPage:
        return self._cached_file(LodpTitleAndPlansPage, title_key)
