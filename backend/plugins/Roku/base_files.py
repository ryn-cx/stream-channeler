# TODO: Validate
from __future__ import annotations

from plugins.Roku.files import ContentFile, SeasonEpisodesFile
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class RokuBaseFiles(BasePlugin):
    # TODO: Validate
    def content_file(self, content_key: str) -> ContentFile:
        return self._cached_file(ContentFile, content_key)

    # TODO: Validate
    def season_episodes_file(self, episode_key: str) -> SeasonEpisodesFile:
        return self._cached_file(SeasonEpisodesFile, episode_key)
