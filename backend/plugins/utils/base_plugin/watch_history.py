# TODO: Validate
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.users.models import User
from app.watches.models import Watch
from app.watches.schemas import WatchImportResult, WatchImportResults
from plugins.utils.base_plugin.watch import WatchMixin


# TODO: Validate
@dataclass
class ParsedWatchEntry:
    """A single parsed entry from a plugin's watch history export."""

    episode_key: str
    watch_date: datetime
    import_result: WatchImportResult


# TODO: Validate
class WatchHistoryMixin(WatchMixin):
    """Base mixin providing the shared `import_watch_history` workflow.

    Subclasses only need to implement :meth:`_parse_watch_history`, which
    turns the raw uploaded content into a list of :class:`ParsedWatchEntry`.
    The base class handles episode lookups, deduplication, `new_only`
    filtering, and result aggregation.
    """

    # TODO: Validate
    @abstractmethod
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        """Parse raw watch history content into entries ready for import."""

    # TODO: Validate
    def import_watch_history(
        self,
        content: str,
        user: User,
        *,
        new_only: bool,
        verified: bool,
    ) -> WatchImportResults:
        parsed_entries = self._parse_watch_history(content)

        episode_keys = [entry.episode_key for entry in parsed_entries]
        episodes_on_database = self._get_episodes_by_key(episode_keys)
        watched_canonical_dates = self._get_watched_canonical_dates(
            user,
            episodes_on_database,
        )

        added_watches: list[WatchImportResult] = []
        existing_watches: list[WatchImportResult] = []
        skipped_watches: list[WatchImportResult] = []

        for entry in parsed_entries:
            episode = episodes_on_database.get(entry.episode_key)
            if episode is None:
                skipped_watches.append(entry.import_result)
                continue

            # A watch is of the episode itself, which every source carrying it
            # has a copy of, so a single watch is recorded for all of them. A
            # copy that is not of anything yet is skipped rather than counted as
            # a watch of nothing.
            canonical_key = episode.canonical_episode.key
            if canonical_key is None:
                skipped_watches.append(entry.import_result)
                continue
            watched_dates = watched_canonical_dates.setdefault(canonical_key, [])
            if (new_only and watched_dates) or entry.watch_date in watched_dates:
                existing_watches.append(entry.import_result)
                continue

            self.session.add(
                Watch(
                    user_id=user.id,
                    episode_id=episode.id,
                    canonical_episode_key=canonical_key,
                    watch_date=entry.watch_date,
                    verified=verified,
                ),
            )
            watched_dates.append(entry.watch_date)
            added_watches.append(entry.import_result)

        return WatchImportResults(
            added=added_watches,
            existing=existing_watches,
            skipped=skipped_watches,
        )
