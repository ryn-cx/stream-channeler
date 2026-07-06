# TODO: Validate
import json
from typing import override

from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult
from plugins.utils.base_plugin.watch_history import (
    ParsedWatchEntry,
)
from plugins.utils.base_plugin.watch_history import (
    WatchHistoryMixin as BaseWatchHistoryMixin,
)


class WatchHistoryMixin(BaseWatchHistoryMixin):
    import_watch_history_file_extension = ".json"

    @classmethod
    def import_watch_history_instructions(cls) -> str:
        return (
            "1. Go to [takeout.google.com](https://takeout.google.com)\n"
            "2. Deselect all products, then select only 'YouTube and YouTube Music'\n"
            "3. Click 'All YouTube data included', then select only 'history'\n"
            "4. Choose JSON format (not HTML)\n"
            "5. Export and download the archive\n"
            "6. Extract the archive and find "
            "'watch-history.json'\n"
            "7. Upload that file here"
        )

    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        """Parse YouTube watch history from Google Takeout JSON content."""
        entries = json.loads(content)
        parsed_entries: list[ParsedWatchEntry] = []
        for entry in entries:
            # TODO: Why do some entries have no titleUrl?
            if "titleUrl" not in entry:
                continue
            # TODO: Is there a better way to do this?
            # Ignore deleted videos
            if "subtitles" not in entry:
                continue

            video_key = entry["titleUrl"].split("=", maxsplit=1)[-1]
            parsed_entries.append(
                ParsedWatchEntry(
                    episode_key=video_key,
                    watch_date=tz_datetime.fromisoformat(entry["time"]),
                    import_result=WatchImportResult(
                        show=entry["subtitles"][0]["name"],
                        show_url=entry["titleUrl"],
                        episode=entry["title"].removeprefix("Watched "),
                        episode_url=entry["titleUrl"],
                    ),
                ),
            )
        return parsed_entries
