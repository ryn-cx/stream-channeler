# TODO: Validate
import json
from typing import override

from app.plugins.plugins.Crunchyroll.upsert import UpsertMixin
from app.plugins.plugins.utils.base_plugin.watch_history import (
    ParsedWatchEntry,
)
from app.plugins.plugins.utils.base_plugin.watch_history import (
    WatchHistoryMixin as BaseWatchHistoryMixin,
)
from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult


class WatchHistoryMixin(BaseWatchHistoryMixin, UpsertMixin, register=False):
    supports_import_watch_history = True
    import_watch_history_file_extension = ".json"

    @classmethod
    @override
    def import_watch_history_instructions(cls) -> str:
        return (
            "1. Use [Itamae](https://github.com/ryn-cx/itamae) to download "
            "your Crunchyroll watch history\n"
            "2. Upload the file here"
        )

    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        entries = json.loads(content)
        parsed_entries: list[ParsedWatchEntry] = []
        for entry in entries:
            episode_key = entry["id"]
            panel = entry["panel"]
            episode_metadata = panel["episode_metadata"]
            parsed_entries.append(
                ParsedWatchEntry(
                    episode_key=episode_key,
                    watch_date=tz_datetime.fromisoformat(entry["date_played"]),
                    import_result=WatchImportResult(
                        show=episode_metadata["series_title"],
                        show_url=self._show_url(episode_metadata["series_id"]),
                        episode=panel["title"],
                        episode_url=self._episode_url(episode_key),
                    ),
                ),
            )
        return parsed_entries
