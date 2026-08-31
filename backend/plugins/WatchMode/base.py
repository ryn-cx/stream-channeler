# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.WatchMode.sources import SourcesMixin


# TODO: Validate
class WatchModeBase(SourcesMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Watchmode"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.watchmode.com/favicon.ico"
