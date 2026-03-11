import json
from typing import override

from app.plugins.plugins.Crunchyroll.upsert import UpsertMixin
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
                "1. Use [Itamae](https://github.com/ryn-cx/itamae) to download "
                "your Crunchyroll watch history\n"
                "2. Upload the file here"
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
        """Import Crunchyroll watch history from Itamae JSON export."""
        entries = json.loads(content)

        entry_episode_keys: list[str] = [entry["id"] for entry in entries]

        episodes_on_database = self._get_episodes_by_key(entry_episode_keys)
        watched_episode_dates = self._get_watched_episode_dates(
            user,
            episodes_on_database,
        )

        added_watches: list[WatchImportEntry] = []
        skipped_watches: list[WatchImportEntry] = []
        existing_watches: list[WatchImportEntry] = []

        for entry, episode_key in zip(entries, entry_episode_keys, strict=True):
            panel = entry["panel"]
            episode_metadata = panel["episode_metadata"]

            import_entry = WatchImportEntry(
                show=episode_metadata["series_title"],
                show_url=self._show_url(episode_metadata["series_id"]),
                episode=panel["title"],
                episode_url=self._episode_url(episode_key),
            )

            if not (episode := episodes_on_database.get(episode_key)):
                skipped_watches.append(import_entry)
                continue

            watch_date = tz_datetime.fromisotimestamp(entry["date_played"])

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
