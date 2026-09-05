# TODO: Validate
from __future__ import annotations

from plugins.Tubi.files import ContentFile
from plugins.utils.base_plugin_v3.base import BasePlugin


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def content_file(self, content_id: str) -> ContentFile:
        """Contains all of a Tubi title's data (title, seasons, episodes)."""
        return self._file(ContentFile, content_id)
