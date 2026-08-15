# TODO: Validate
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.canonical_media.filters import canonical_id_of
from app.users.models import User
from app.watches.models import Watch
from app.watches.schemas import WatchImportResult, WatchImportResults
from plugins.utils.base_plugin.watch import WatchMixin


# TODO: Validate
@dataclass
class ParsedWatchEntry:
    """A single parsed entry from a plugin's watch history export.

    `verified` is what the file itself says the watch is, and is None for a
    format that does not record it, which leaves the import's own setting to
    say what the watch is.
    """

    episode_key: str
    watch_date: datetime
    import_result: WatchImportResult
    verified: bool | None = None


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
        watched_dates_by_episode = self._get_watched_dates_by_canonical_id(
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

            # A watch is recorded against the link that played it and carries
            # that link's own identifier. Whether the episode has already been
            # watched is asked of every link to it, so importing one website's
            # history does not re-record what another website already recorded.
            watched_dates = watched_dates_by_episode.setdefault(
                canonical_id_of(episode),
                [],
            )
            if (new_only and watched_dates) or entry.watch_date in watched_dates:
                existing_watches.append(entry.import_result)
                continue

            self.session.add(
                Watch(
                    user_id=user.id,
                    episode_id=episode.id,
                    watch_identifier=episode.watch_identifier,
                    watch_date=entry.watch_date,
                    verified=verified if entry.verified is None else entry.verified,
                ),
            )
            watched_dates.append(entry.watch_date)
            added_watches.append(entry.import_result)

        return WatchImportResults(
            added=added_watches,
            existing=existing_watches,
            skipped=skipped_watches,
        )
