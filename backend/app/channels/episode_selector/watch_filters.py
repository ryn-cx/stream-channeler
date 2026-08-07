# TODO: Validate
"""What a `User` has watched, as the episode query reads it.

A `Watch` points at one website's copy of an episode, but it counts for every
copy of that episode, so everything here goes through the `episode_identifier`
the copies share rather than through the episode a watch happens to name.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import case
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, and_, col, desc, func, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.users.models import User
from app.watches.models import Watch

# The episode a watch points at. Watches link to a specific episode, but they still
# count for every episode sharing that episode's `episode_identifier`, so reads join
# through this alias to reach the identifier a watch stands for.
WatchedEpisode = aliased(Episode)

# Labels used to compose raw SQL references from Postgres subquery + column
# names. Callers of `literal_column` rely on the producing subquery being
# materialised with exactly these names; keep them in sync.
EPISODE_LAST_WATCHED_SUBQUERY = "episode_last_watched"
EPISODE_LAST_WATCH_COMPLETED_COLUMN = "episode_last_watch_completed_date"
EPISODE_LAST_WATCH_INCOMPLETE_COLUMN = "episode_last_watch_incomplete_date"

# Maps each last-watched sort field to the subquery column holding its latest
# watch date. Aggregated per episode (not per show) so an episode is ranked by
# its own watch history. Completed = verified watches; incomplete = unverified
# (partial) watches.
LAST_WATCHED_COLUMNS = {
    "last_watched_completed": EPISODE_LAST_WATCH_COMPLETED_COLUMN,
    "last_watched_incomplete": EPISODE_LAST_WATCH_INCOMPLETE_COLUMN,
}


def verified_watch_identifiers(user: User) -> SelectOfScalar[str]:
    """Episode identifiers the `User` has a verified watch of."""
    return (
        select(WatchedEpisode.episode_identifier)
        .join(Watch, col(Watch.episode_id) == col(WatchedEpisode.id))
        .where(
            and_(
                Watch.user_id == user.id,
                col(Watch.verified).is_(True),
            ),
        )
    )


def any_watch_identifiers(user: User) -> SelectOfScalar[str]:
    """Episode identifiers with any watch (verified or not) for the user."""
    return (
        select(WatchedEpisode.episode_identifier)
        .join(Watch, col(Watch.episode_id) == col(WatchedEpisode.id))
        .where(Watch.user_id == user.id)
    )


def hide_watched_condition(
    user: User,
    maximum_watch_date: datetime | None,
) -> ColumnElement[bool]:
    """Keep only episodes the `User` has not finished.

    Watched = has a verified watch. Partially watched (unverified) and unwatched
    episodes are kept. A `maximum_watch_date` treats a watch older than it as no
    longer counting, so a rewatch comes back around.
    """
    watched = verified_watch_identifiers(user)
    if maximum_watch_date:
        watched = watched.where(Watch.watch_date > maximum_watch_date)
    return col(Episode.episode_identifier).not_in(watched)


def hide_unwatched_condition(user: User) -> ColumnElement[bool]:
    """Keep only episodes the `User` has some watch of.

    Unwatched = no watch at all. Partially watched (unverified) and verified
    episodes are kept.
    """
    return col(Episode.episode_identifier).in_(any_watch_identifiers(user))


def hide_partially_watched_condition(user: User) -> ColumnElement[bool]:
    """Drop episodes the `User` started and never finished.

    Partially watched = has a watch but none verified. Unwatched and verified
    episodes are kept.
    """
    return or_(
        col(Episode.episode_identifier).not_in(any_watch_identifiers(user)),
        col(Episode.episode_identifier).in_(verified_watch_identifiers(user)),
    )


def started_show_ids(user: User) -> SelectOfScalar[UUID]:
    """The ids of every `Show` the `User` has watched anything of."""
    return (
        select(Show.id)
        .join(Season, col(Show.id) == Season.show_id)
        .join(Episode, col(Season.id) == Episode.season_id)
        .join(Episode.watches.and_(Watch.user_id == user.id))  # type: ignore[attr-defined]
        .distinct()
    )


def join_last_watched(
    query: Select[tuple[Episode, UUID]],
    user: User,
) -> Select[tuple[Episode, UUID]]:
    """Join in each episode's latest completed and incomplete watch dates.

    Named exactly as `LAST_WATCHED_COLUMNS` says, since the sort expressions
    reach these columns as raw SQL rather than through the subquery object.
    """
    last_watched = (
        select(
            WatchedEpisode.episode_identifier,
            func.max(
                case((col(Watch.verified).is_(True), Watch.watch_date)),
            ).label(EPISODE_LAST_WATCH_COMPLETED_COLUMN),
            func.max(
                case((col(Watch.verified).is_(False), Watch.watch_date)),
            ).label(EPISODE_LAST_WATCH_INCOMPLETE_COLUMN),
        )
        .select_from(Watch)
        .join(WatchedEpisode, col(Watch.episode_id) == col(WatchedEpisode.id))
        .where(col(Watch.user_id) == user.id)
        .group_by(col(WatchedEpisode.episode_identifier))
        .subquery(EPISODE_LAST_WATCHED_SUBQUERY)
    )

    return query.outerjoin(
        last_watched,
        col(Episode.episode_identifier) == last_watched.c.episode_identifier,
    )


def latest_watch_by_identifier(
    session: Session,
    user: User,
    episodes: Sequence[Episode],
) -> dict[str, Watch]:
    """The `User`'s most recent `Watch` of each episode, keyed by identifier."""
    if not episodes:
        return {}

    identifiers = [episode.episode_identifier for episode in episodes]
    rows = session.exec(
        select(WatchedEpisode.episode_identifier, Watch)  # type: ignore[call-overload]
        .join(Watch, col(Watch.episode_id) == col(WatchedEpisode.id))
        .where(
            col(WatchedEpisode.episode_identifier).in_(identifiers),
            Watch.user_id == user.id,
        )
        .order_by(
            col(WatchedEpisode.episode_identifier),
            desc(Watch.watch_date),
            desc(Watch.id),
        )
        .distinct(col(WatchedEpisode.episode_identifier)),
    ).all()

    return dict(rows)
