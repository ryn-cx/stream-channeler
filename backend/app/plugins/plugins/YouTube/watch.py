# TODO: Validate
import json
from typing import override

from app.plugins.plugins.YouTube.upsert import UpsertMixin
from app.users.models import User
from app.utils import tz_datetime
from app.watches.models import Watch
from app.watches.schemas import (
    WatchImportEntry,
    WatchImportFormatInformation,
    WatchImportResult,
)


class WatchMixin(UpsertMixin, register=False):
    # region Watch Import

    @classmethod
    @override
    def import_watch_history_info(cls) -> WatchImportFormatInformation:
        return WatchImportFormatInformation(
            plugin_id=cls.plugin_id(),
            plugin_name=cls._plugin_name(),
            file_type="JSON",
            file_extension=".json",
            instructions=(
                "1. Go to [takeout.google.com](https://takeout.google.com)\n"
                "2. Deselect all products, then select only 'YouTube and YouTube Music'\n"
                "3. Click 'All YouTube data included', then select only 'history'\n"
                "4. Choose JSON format (not HTML)\n"
                "5. Export and download the archive\n"
                "6. Extract the archive and find "
                "'watch-history.json'\n"
                "7. Upload that file here"
            ),
        )

    @override
    def import_watch_history(
        self,
        content: str,
        user: User,
        *,
        new_only: bool,
        verified: bool,
    ) -> WatchImportResult:
        """Import YouTube watch history from Google Takeout JSON content."""
        entries = json.loads(content)

        entry_video_keys: list[str] = []
        for entry in entries:
            video_key = entry["titleUrl"].split("=", maxsplit=1)[-1]
            entry_video_keys.append(video_key)

        episodes_on_database = self._get_episodes_by_key(entry_video_keys)
        watched_episode_dates = self._get_watched_episode_dates(
            user,
            episodes_on_database,
        )

        added_watches: list[WatchImportEntry] = []
        skipped_watches: list[WatchImportEntry] = []
        existing_watches: list[WatchImportEntry] = []

        for entry, video_key in zip(entries, entry_video_keys, strict=True):
            # Ignore deleted videos
            if "subtitles" not in entry:
                continue

            import_entry = WatchImportEntry(
                show=entry["subtitles"][0]["name"],
                show_url=entry["titleUrl"],
                episode=entry["title"].removeprefix("Watched "),
                episode_url=entry["titleUrl"],
            )

            if not (episode := episodes_on_database.get(video_key)):
                skipped_watches.append(import_entry)
                continue

            watch_date = tz_datetime.fromisotimestamp(entry["time"])

            watched_dates = watched_episode_dates.setdefault(str(episode.id), [])
            if new_only and watched_dates:
                existing_watches.append(import_entry)
                continue

            if watch_date in watched_dates:
                existing_watches.append(import_entry)
                continue

            self.db.add(
                Watch(
                    user_id=user.id,
                    episode_id=episode.id,
                    watch_date=watch_date,
                    verified=verified,
                ),
            )
            watched_dates.append(watch_date)
            added_watches.append(import_entry)

        return WatchImportResult(
            added=added_watches,
            existing=existing_watches,
            skipped=skipped_watches,
        )

    # endregion Watch Import
