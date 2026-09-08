# TODO: Validate
from __future__ import annotations

from plugins.Tubi.files import ContentFile
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class TubiBaseFiles(BasePlugin):
    # TODO: Validate
    def content_file(self, content_id: str) -> ContentFile:
        """Contains all of a Tubi title's data (title, seasons, episodes)."""
        return self._cached_file(ContentFile, content_id)
