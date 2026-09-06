# TODO: Validate
from __future__ import annotations

from plugins.utils.base_plugin.base import BasePlugin
from plugins.WatchMode.files import TitleSources


# TODO: Validate
class BasicFiles(BasePlugin):
    # TODO: Validate
    def title_sources_file(self, title_key: str) -> TitleSources:
        """Return the listing file for the Watchmode title id `title_key`."""
        return self._file(TitleSources, title_key)
