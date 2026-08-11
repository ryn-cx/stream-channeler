# TODO: Validate
from __future__ import annotations

import json
from typing import override

from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult
from plugins.Crunchyroll.helpers import HelperMixin
from plugins.utils.base_plugin.watch_history import (
    ParsedWatchEntry,
)
from plugins.utils.base_plugin.watch_history import (
    WatchHistoryMixin as BaseWatchHistoryMixin,
)


# TODO: Validate
class WatchHistoryMixin(BaseWatchHistoryMixin, HelperMixin, register=False):
    import_watch_history_file_extension = ".json"

    # TODO: Validate
    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        return [
            ParsedWatchEntry(
                episode_key=entry["id"],
                watch_date=tz_datetime.fromisoformat(entry["date_played"]),
                import_result=WatchImportResult(
                    show=entry["panel"]["episode_metadata"]["series_title"],
                    show_url=self._series_url(
                        entry["panel"]["episode_metadata"]["series_id"],
                    ),
                    episode=entry["panel"]["title"],
                    episode_url=self._episode_url(entry["id"]),
                ),
            )
            for entry in json.loads(content)
        ]
