# TODO: Validate
"""What a `User` has watched, as the episode query reads it.

A `Watch` is recorded against one website's copy of an episode but is of the
episode itself, so everything here reads the `canonical_episode_key` the watch
carries. That makes a watch count for every copy of what was watched, and go on
counting once the copy it was made against has been deleted.

The key is what names the episode, so the canonical rows a watch counts for are
the rows carrying that key. Where the same media is reached two ways and so has
a row under each, one watch counts for both, which is what carrying the same key
means.
"""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import case
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, desc, func, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.canonical_episodes.models import CanonicalEpisode
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.users.models import User
from app.watches.models import Watch

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


# TODO: Validate
def watched_canonical_episodes(user: User) -> SelectOfScalar[UUID]:
    """The canonical episodes carrying a key the `User` has watched."""
    return (
        select(col(CanonicalEpisode.id))
        .join(
            Watch,
            col(Watch.canonical_episode_key) == col(CanonicalEpisode.key),
        )
        .where(Watch.user_id == user.id)
    )


# TODO: Validate
def verified_watch_identifiers(user: User) -> SelectOfScalar[UUID]:
    """The canonical episodes the `User` has a verified watch of."""
    return watched_canonical_episodes(user).where(col(Watch.verified).is_(True))


# TODO: Validate
def any_watch_identifiers(user: User) -> SelectOfScalar[UUID]:
    """The canonical episodes with any watch (verified or not) for the user."""
    return watched_canonical_episodes(user)


# TODO: Validate
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
    return col(Episode.canonical_episode_id).not_in(watched)


# TODO: Validate
def hide_unwatched_condition(user: User) -> ColumnElement[bool]:
    """Keep only episodes the `User` has some watch of.

    Unwatched = no watch at all. Partially watched (unverified) and verified
    episodes are kept.
    """
    return col(Episode.canonical_episode_id).in_(any_watch_identifiers(user))


# TODO: Validate
def hide_partially_watched_condition(user: User) -> ColumnElement[bool]:
    """Drop episodes the `User` started and never finished.

    Partially watched = has a watch but none verified. Unwatched and verified
    episodes are kept.
    """
    return or_(
        col(Episode.canonical_episode_id).not_in(any_watch_identifiers(user)),
        col(Episode.canonical_episode_id).in_(verified_watch_identifiers(user)),
    )


# TODO: Validate
def started_show_ids(user: User) -> SelectOfScalar[UUID]:
    """The ids of every `Show` the `User` has watched anything of."""
    return (
        select(Show.id)
        .join(Season, col(Show.id) == Season.show_id)
        .join(Episode, col(Season.id) == Episode.season_id)
        .join(Episode.watches.and_(Watch.user_id == user.id))  # type: ignore[attr-defined]
        .distinct()
    )


# TODO: Validate
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
            col(CanonicalEpisode.id).label("canonical_episode_id"),
            func.max(
                case((col(Watch.verified).is_(True), Watch.watch_date)),
            ).label(EPISODE_LAST_WATCH_COMPLETED_COLUMN),
            func.max(
                case((col(Watch.verified).is_(False), Watch.watch_date)),
            ).label(EPISODE_LAST_WATCH_INCOMPLETE_COLUMN),
        )
        .select_from(Watch)
        .join(
            CanonicalEpisode,
            col(CanonicalEpisode.key) == col(Watch.canonical_episode_key),
        )
        .where(col(Watch.user_id) == user.id)
        .group_by(col(CanonicalEpisode.id))
        .subquery(EPISODE_LAST_WATCHED_SUBQUERY)
    )

    return query.outerjoin(
        last_watched,
        col(Episode.canonical_episode_id) == last_watched.c.canonical_episode_id,
    )


# TODO: Validate
def latest_watch_by_identifier(
    session: Session,
    user: User,
    episodes: Sequence[Episode],
) -> dict[UUID, Watch]:
    """The `User`'s most recent `Watch` of each episode, keyed by canonical id."""
    if not episodes:
        return {}

    identifiers = [episode.canonical_episode_id for episode in episodes]
    rows = session.exec(
        select(col(CanonicalEpisode.id), Watch)  # type: ignore[call-overload]
        .join(
            CanonicalEpisode,
            col(CanonicalEpisode.key) == col(Watch.canonical_episode_key),
        )
        .where(
            col(CanonicalEpisode.id).in_(identifiers),
            Watch.user_id == user.id,
        )
        .order_by(
            col(CanonicalEpisode.id),
            desc(Watch.watch_date),
            desc(Watch.id),
        )
        .distinct(col(CanonicalEpisode.id)),
    ).all()

    return dict(rows)
