# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.YouTube.constants import LONG_DOMAIN, SHORT_DOMAIN
from plugins.YouTube.source import SourceMixin
from plugins.YouTube.updater import UpdaterMixin
from plugins.YouTube.upsert import UpsertMixin
from plugins.YouTube.watch_history import WatchHistoryMixin


# TODO: Validate
class YouTubeBase(SourceMixin, UpsertMixin, WatchHistoryMixin, UpdaterMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "YouTube"

    # TODO: Validate
    @classmethod
    @override
    def specialized_updater(cls) -> bool:
        return True

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return (
            "https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png"
        )

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        return [LONG_DOMAIN, SHORT_DOMAIN]
