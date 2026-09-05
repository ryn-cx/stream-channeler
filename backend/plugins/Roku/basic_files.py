# TODO: Validate
from __future__ import annotations

from plugins.Roku.files import ContentFile, SeasonEpisodesFile
from plugins.utils.base_plugin_v3.base import BasePlugin


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def content_file(self, content_key: str) -> ContentFile:
        return self._file(ContentFile, content_key)

    # TODO: Validate
    def season_episodes_file(self, episode_key: str) -> SeasonEpisodesFile:
        return self._file(SeasonEpisodesFile, episode_key)
