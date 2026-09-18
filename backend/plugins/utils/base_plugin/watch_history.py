# TODO: Validate
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import override

from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.episodes import tmdb_record_id_of
from app.users.models import User
from app.watches.identifiers import watched_dates_by_tmdb_record_id
from app.watches.models import Watch
from app.watches.schemas import WatchImportResult, WatchImportResults
from plugins.utils.abstract_plugin import AbstractPlugin


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


# TODO: Validate
class BaseWatchHistoryMixin(AbstractPlugin, ABC):
    session: Session
    plugin: Plugin

    # TODO: Validate
    def _get_episodes_by_key(self, episode_keys: list[str]) -> dict[str, Episode]:
        """Load this plugin's `Episode` for each key.

        A watch is of the episode itself rather than of one website's non-canonical row,
        so recording a single watch per key is enough - no per-source duplication is
        needed.
        """
        if not episode_keys:
            return {}
        statement = (
            select(Episode)
            .join(Season, col(Episode.season_id) == col(Season.id))
            .join(Title, col(Season.title_id) == col(Title.id))
            .join(Source)
            .where(Source.plugin_id == self.plugin.id)
            .where(col(Episode.key).in_(episode_keys))
        )
        return {episode.key: episode for episode in self.session.exec(statement)}

    # TODO: Validate
    def _get_watched_dates_by_tmdb_record_id(
        self,
        user: User,
        episodes_by_key: dict[str, Episode],
    ) -> dict[uuid.UUID, list[datetime]]:
        """Load watched dates grouped by the episode they are of.

        A watch is recorded against the one link that played it, so a date is
        looked up across every link to the same episode rather than under the
        link this import happens to be walking. A row that links to nothing is
        the episode itself rather than a row with no episode behind it, so it is
        its own group - which is the whole of a plugin nothing has been minted
        for.
        """
        return watched_dates_by_tmdb_record_id(
            self.session,
            user.id,
            {tmdb_record_id_of(episode) for episode in episodes_by_key.values()},
        )

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
    @override
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
        watched_dates_by_episode = self._get_watched_dates_by_tmdb_record_id(
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

            watched_dates = watched_dates_by_episode.setdefault(
                tmdb_record_id_of(episode),
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
