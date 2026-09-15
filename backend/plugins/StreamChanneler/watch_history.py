# TODO: Validate
from __future__ import annotations

import json
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, override

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import col, func, or_, select

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.episodes import (
    links_of,
    tmdb_episode_id_column,
    tmdb_episode_link,
)
from app.tmdb_media.filters import (
    is_linked,
    is_not_linked,
)
from app.watches.models import Watch
from app.watches.schemas import WatchExportEntry, WatchImportResult
from plugins.utils.base_plugin.watch_history import (
    BaseWatchHistoryMixin,
    ParsedWatchEntry,
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
        title=watch_identifier,
        title_url="",
        episode=watch_identifier,
        episode_url="",
    )


# TODO: Validate
class StreamChannelerWatchHistoryMixin(BaseWatchHistoryMixin):
    import_watch_history_file_extension = ".json"

    # TODO: Validate
    def export_watch_history(self, user: User) -> list[WatchExportEntry]:
        named_episode = aliased(Episode)
        named_link = tmdb_episode_link()
        watched_episode = aliased(Episode)
        statement = (
            select(
                func.coalesce(
                    col(watched_episode.watch_identifier),
                    col(Watch.watch_identifier),
                ),
                Watch.watch_date,
                Watch.verified,
            )
            .select_from(Watch)
            .outerjoin(
                named_episode,
                col(named_episode.watch_identifier) == col(Watch.watch_identifier),
            )
            .outerjoin(named_link, links_of(named_episode, named_link))
            .outerjoin(
                watched_episode,
                col(watched_episode.id)
                == tmdb_episode_id_column(named_episode, named_link),
            )
            .where(Watch.user_id == user.id)
            .distinct()
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
        if not episode_keys:
            return {}
        wanted = set(episode_keys)
        # The episode a link is of is the same table reached again, so which of
        # the two each side means is said outright rather than left to the join.
        tmdb_episode = aliased(Episode)
        tmdb_link = tmdb_episode_link()
        links = self._by_named_episode(
            wanted,
            self.session.exec(
                select(Episode, tmdb_episode)  # type: ignore[call-overload]
                .select_from(Episode)
                .join(tmdb_link, links_of(Episode, tmdb_link))
                .join(
                    tmdb_episode,
                    col(tmdb_link.tmdb_episode_id) == col(tmdb_episode.id),
                )
                .where(
                    is_linked(Episode),
                    is_not_linked(tmdb_episode),
                    self._names_clause(tmdb_episode, wanted),
                    col(Episode.deleted_at).is_(None),
                ),
            ),
        )
        own = self._by_named_episode(
            wanted,
            (
                (episode, episode)
                for episode in self.session.exec(
                    select(Episode)
                    .select_from(Episode)
                    .join(Season, col(Episode.season_id) == col(Season.id))
                    .join(Title, col(Season.title_id) == col(Title.id))
                    .where(
                        is_not_linked(Episode),
                        is_not_linked(Title),
                        self._names_clause(Episode, wanted),
                        col(Episode.deleted_at).is_(None),
                    ),
                )
            ),
        )
        named_links = self._by_named_episode(
            wanted,
            (
                (episode, episode)
                for episode in self.session.exec(
                    select(Episode).where(
                        is_linked(Episode),
                        col(Episode.watch_identifier).in_(wanted),
                        col(Episode.deleted_at).is_(None),
                    ),
                )
            ),
        )
        # A link named outright is the most exact of the three, and the episode
        # a link is of is more use than a row TMDB wrote, so each overrides what
        # came before it.
        return own | links | named_links

    # TODO: Validate
    @staticmethod
    def _names_clause(entity: Any, wanted: set[str]) -> ColumnElement[bool]:  # noqa: ANN401 - A model class or an alias of one.
        """Match `entity` against what an export calls it, of either vintage."""
        return or_(
            col(entity.watch_identifier).in_(wanted),
            col(entity.key).in_(wanted),
        )

    # TODO: Validate
    @staticmethod
    def _by_named_episode(
        wanted: set[str],
        rows: Iterable[tuple[Episode, Episode]],
    ) -> dict[str, Episode]:
        """Key each row by whichever of the episode's names the export used."""
        found: dict[str, Episode] = {}
        for episode, named in rows:
            for name in (named.watch_identifier, named.key):
                if name in wanted:
                    found.setdefault(name, episode)
        return found

    # TODO: Validate
    def _import_results_by_identifier(
        self,
        watch_identifiers: list[str],
    ) -> dict[str, WatchImportResult]:
        if not watch_identifiers:
            return {}
        statement = (
            select(Episode, Title)
            .select_from(Episode)
            .join(
                Season,
                col(Episode.season_id) == col(Season.id),
            )
            .join(
                Title,
                col(Season.title_id) == col(Title.id),
            )
            .where(
                is_not_linked(Episode),
                is_not_linked(Title),
                self._names_clause(Episode, set(watch_identifiers)),
            )
        )
        wanted = set(watch_identifiers)
        return {
            name: WatchImportResult(
                title=tmdb_title.name or tmdb_episode.key,
                title_url=tmdb_title.url or "",
                episode=tmdb_episode.name or tmdb_episode.key,
                episode_url=tmdb_episode.url or "",
            )
            for tmdb_episode, tmdb_title in self.session.exec(statement)
            for name in (tmdb_episode.watch_identifier, tmdb_episode.key)
            if name in wanted
        }
