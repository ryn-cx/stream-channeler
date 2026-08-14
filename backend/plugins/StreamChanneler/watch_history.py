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
def _unknown_import_result(watch_identifier: str) -> WatchImportResult:
    """Describe an entry naming an episode this database has never seen.

    The identifier is the whole of what is known about it, so it is what gets
    shown.
    """
    return WatchImportResult(
        show=watch_identifier,
        show_url="",
        episode=watch_identifier,
        episode_url="",
    )


# TODO: Validate
class WatchHistoryMixin(BaseWatchHistoryMixin):
    """Export and import watches as Stream Channeler's own history file.

    Every other plugin keys its export on the website's own episode ids, which
    only that website's links carry. A Stream Channeler export is of watches that
    were made here, so it is keyed on the episode itself, which is what a `Watch`
    holds and what survives a link being deleted or swapped for another
    website's.
    """

    import_watch_history_file_extension = ".json"

    # TODO: Validate
    def export_watch_history(self, user: User) -> list[WatchExportEntry]:
        """Return the `User`'s watches, holding only what re-importing them needs.

        Names, urls and ids are all re-read from whatever database the file is
        imported into, so a watch is nothing more than which episode it is of,
        when it happened, and whether it was verified.
        """
        statement = (
            select(Watch.watch_identifier, Watch.watch_date, Watch.verified)
            .where(Watch.user_id == user.id)
            .order_by(col(Watch.watch_date))
        )
        return [
            WatchExportEntry(
                watch_identifier=watch_identifier,
                watch_date=watch_date,
                verified=verified,
            )
            for watch_identifier, watch_date, verified in self.session.exec(statement)
        ]

    # TODO: Validate
    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        entries = [
            WatchExportEntry.model_validate(entry) for entry in json.loads(content)
        ]
        import_results = self._import_results_by_identifier(
            [entry.watch_identifier for entry in entries],
        )
        return [
            ParsedWatchEntry(
                episode_key=entry.watch_identifier,
                watch_date=entry.watch_date.astimezone(),
                import_result=import_results.get(entry.watch_identifier)
                or _unknown_import_result(entry.watch_identifier),
                verified=entry.verified,
            )
            for entry in entries
        ]

    # TODO: Validate
    @override
    def _get_episodes_by_key(self, episode_keys: list[str]) -> dict[str, Episode]:
        """Load one row for each episode the exported identifiers name.

        The identifiers are of the episodes themselves rather than of one
        plugin's links to them, so the lookup runs across every plugin instead of
        being held to this one's sources, which have no episodes of their own.

        An episode nothing else holds a record of is the record, and is watched
        where it stands, so it answers for its own identifier. A link is
        preferred where both are stored, since the episode a link is of may be a
        row TMDB wrote and nothing is watched there.
        """
        if not episode_keys:
            return {}
        # The episode a link is of is the same table reached again, so which of
        # the two each side means is said outright rather than left to the join.
        canonical_episode = aliased(Episode)
        links = {
            episode.canonical_episode.watch_identifier: episode
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
                    col(canonical_episode.watch_identifier).in_(episode_keys),
                    col(Episode.deleted_at).is_(None),
                ),
            )
            if episode.canonical_episode is not None
        }
        own = {
            episode.watch_identifier: episode
            for episode in self.session.exec(
                select(Episode)
                .select_from(Episode)
                .join(Season, col(Episode.season_id) == col(Season.id))
                .join(Show, col(Season.show_id) == col(Show.id))
                .where(
                    is_canonical(Episode),
                    is_canonical(Show),
                    col(Episode.watch_identifier).in_(episode_keys),
                    col(Episode.deleted_at).is_(None),
                ),
            )
        }
        return own | links

    # TODO: Validate
    def _import_results_by_identifier(
        self,
        watch_identifiers: list[str],
    ) -> dict[str, WatchImportResult]:
        """Describe each exported identifier for the import summary.

        An export holds no titles, so they are read back out of the database it
        is being imported into.
        """
        if not watch_identifiers:
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
                col(Episode.watch_identifier).in_(watch_identifiers),
            )
        )
        return {
            canonical_episode.watch_identifier: WatchImportResult(
                show=canonical_show.name or canonical_episode.key,
                show_url=canonical_show.url or "",
                episode=canonical_episode.name or canonical_episode.key,
                episode_url=canonical_episode.url or "",
            )
            for canonical_episode, canonical_show in self.session.exec(statement)
            if canonical_episode.key is not None
        }
