# TODO: Validate
from __future__ import annotations

import json
from typing import override

from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult
from plugins.Crunchyroll.importer import CrunchyrollAnimeImporter
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.utils.base_plugin.watch_history import (
    BaseWatchHistoryMixin,
    ParsedWatchEntry,
)


# TODO: Validate
class CrunchyrollWatchHistoryMixin(BaseWatchHistoryMixin, CrunchyrollShared):
    import_watch_history_file_extension = ".json"

    # TODO: Validate
    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        return [
            ParsedWatchEntry(
                episode_key=entry["id"],
                watch_date=tz_datetime.fromisoformat(entry["date_played"]),
                import_result=WatchImportResult(
                    title=entry["panel"]["episode_metadata"]["series_title"],
                    title_url=CrunchyrollAnimeImporter.title_url(
                        entry["panel"]["episode_metadata"]["series_id"],
                    ),
                    episode=entry["panel"]["title"],
                    episode_url=CrunchyrollAnimeImporter.episode_url(entry["id"]),
                ),
            )
            for entry in json.loads(content)
        ]
