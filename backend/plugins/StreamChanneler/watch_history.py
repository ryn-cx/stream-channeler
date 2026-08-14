# TODO: Validate
from __future__ import annotations

import json
from typing import TYPE_CHECKING, override

from sqlalchemy.orm import aliased
from sqlmodel import col, select

from app.canonical_media.filters import is_canonical, is_non_canonical
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.watches.models import Watch
from app.watches.schemas import WatchExportEntry, WatchImportResult
from plugins.utils.base_plugin.watch_history import (
    ParsedWatchEntry,
)
from plugins.utils.base_plugin.watch_history import (
    WatchHistoryMixin as BaseWatchHistoryMixin,
)

if TYPE_CHECKING:
    from app.users.models import User


# TODO: Validate
def _unknown_import_result(episode_key: str) -> WatchImportResult:
    """Describe an entry naming an episode this database has never seen.

    The key is the whole of what is known about it, so it is what gets shown.
    """
    return WatchImportResult(
        show=episode_key,
        show_url="",
        episode=episode_key,
        episode_url="",
    )


# TODO: Validate
class WatchHistoryMixin(BaseWatchHistoryMixin):
    """Export and import watches as Stream Channeler's own history file.

    Every other plugin keys its export on the website's own episode ids, which
    only that website's copies carry. A Stream Channeler export is of watches
    that were made here, so it is keyed on the episode itself, which is what a
    `Watch` holds and what survives a copy being deleted or swapped for another
    website's.
    """

    import_watch_history_file_extension = ".json"

    # TODO: Validate
    def export_watch_history(self, user: User) -> list[WatchExportEntry]:
        """Return the `User`'s watches, holding only what re-importing them needs.

        Names, urls and ids are all re-read from whatever database the file is
        imported into, so a watch is nothing more than which episode it is of
        and when it happened.
        """
        statement = (
            select(Watch.canonical_episode_key, Watch.watch_date)
            .where(Watch.user_id == user.id)
            .order_by(col(Watch.watch_date))
        )
        return [
            WatchExportEntry(canonical_episode_key=key, watch_date=watch_date)
            for key, watch_date in self.session.exec(statement)
        ]

    # TODO: Validate
    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        entries = [
            WatchExportEntry.model_validate(entry) for entry in json.loads(content)
        ]
        import_results = self._import_results_by_key(
            [entry.canonical_episode_key for entry in entries],
        )
        return [
            ParsedWatchEntry(
                episode_key=entry.canonical_episode_key,
                watch_date=entry.watch_date.astimezone(),
                import_result=import_results.get(entry.canonical_episode_key)
                or _unknown_import_result(entry.canonical_episode_key),
            )
            for entry in entries
        ]

    # TODO: Validate
    @override
    def _get_episodes_by_key(self, episode_keys: list[str]) -> dict[str, Episode]:
        """Load one copy of each episode the exported keys name.

        The keys are of the episodes themselves rather than of one plugin's
        copies of them, so the lookup runs across every plugin instead of being
        held to this one's sources, which have no episodes of their own.

        An episode nothing else holds a record of is the record, and is watched
        where it stands, so it answers for its own key. A copy is preferred where
        both are stored, since the episode a copy is of may be a row TMDB wrote
        and nothing is watched there.
        """
        if not episode_keys:
            return {}
        # The episode a copy is of is the same table reached again, so which of
        # the two each side means is said outright rather than left to the join.
        canonical_episode = aliased(Episode)
        copies = {
            episode.canonical_episode.key: episode
            for episode in self.session.exec(
                select(Episode)
                .select_from(Episode)
                .join(
                    canonical_episode,
                    col(Episode.canonical_episode_id) == col(canonical_episode.id),
                )
                .where(
                    is_non_canonical(Episode),
                    is_canonical(canonical_episode),
                    col(canonical_episode.key).in_(episode_keys),
                    col(Episode.deleted_at).is_(None),
                ),
            )
            if episode.canonical_episode is not None
        }
        own = {
            episode.key: episode
            for episode in self.session.exec(
                select(Episode)
                .select_from(Episode)
                .join(Season, col(Episode.season_id) == col(Season.id))
                .join(Show, col(Season.show_id) == col(Show.id))
                .where(
                    is_canonical(Episode),
                    is_canonical(Show),
                    col(Episode.key).in_(episode_keys),
                    col(Episode.deleted_at).is_(None),
                ),
            )
        }
        return own | copies

    # TODO: Validate
    def _import_results_by_key(
        self,
        episode_keys: list[str],
    ) -> dict[str, WatchImportResult]:
        """Describe each exported key for the import summary.

        An export holds no titles, so they are read back out of the database it
        is being imported into.
        """
        if not episode_keys:
            return {}
        statement = (
            select(Episode, Show)
            .select_from(Episode)
            .join(
                Season,
                col(Episode.season_id) == col(Season.id),
            )
            .join(
                Show,
                col(Season.show_id) == col(Show.id),
            )
            .where(
                is_canonical(Episode),
                is_canonical(Show),
                col(Episode.key).in_(episode_keys),
            )
        )
        return {
            canonical_episode.key: WatchImportResult(
                show=canonical_show.name or canonical_episode.key,
                show_url=canonical_show.url or "",
                episode=canonical_episode.name or canonical_episode.key,
                episode_url=canonical_episode.url or "",
            )
            for canonical_episode, canonical_show in self.session.exec(statement)
            if canonical_episode.key is not None
        }
