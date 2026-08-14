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
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, desc, func, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.canonical_media.filters import (
    canonical_id_of,
    is_canonical,
)
from app.channels.episode_selector.canonical_entities import episode_id
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
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
    watched_episode = aliased(Episode)
    return (
        select(col(watched_episode.id))
        .join(
            Watch,
            col(Watch.canonical_episode_key) == col(watched_episode.key),
        )
        .where(is_canonical(watched_episode), Watch.user_id == user.id)
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
    return episode_id().not_in(watched)


# TODO: Validate
def hide_unwatched_condition(user: User) -> ColumnElement[bool]:
    """Keep only episodes the `User` has some watch of.

    Unwatched = no watch at all. Partially watched (unverified) and verified
    episodes are kept.
    """
    return episode_id().in_(any_watch_identifiers(user))


# TODO: Validate
def hide_partially_watched_condition(user: User) -> ColumnElement[bool]:
    """Drop episodes the `User` started and never finished.

    Partially watched = has a watch but none verified. Unwatched and verified
    episodes are kept.
    """
    return or_(
        episode_id().not_in(any_watch_identifiers(user)),
        episode_id().in_(verified_watch_identifiers(user)),
    )


# TODO: Validate
def started_show_ids(user: User) -> SelectOfScalar[UUID]:
    """The titles the `User` has watched anything of.

    The titles themselves rather than the websites' listings of them, since a
    watch is of the episode rather than of the copy that played it and a title
    started on one website is started wherever else it is carried. An episode
    nothing was minted for it to be a copy of hangs off a website's own listing,
    so the titles it counts towards are the ones that listing is a copy of - all
    of them, since a listing is no more a copy of one title than of another.
    """
    watched_episode = aliased(Episode)
    watched_season = aliased(Season)
    watched_show = aliased(Show)
    watched_link = aliased(ShowCanonicalShow)
    return (
        select(
            func.coalesce(
                col(watched_link.canonical_show_id),
                col(watched_show.id),
            ),
        )
        .select_from(watched_season)
        .join(
            watched_episode,
            col(watched_episode.season_id) == col(watched_season.id),
        )
        .join(watched_show, col(watched_season.show_id) == col(watched_show.id))
        # A title has no links and stands for itself; a listing has one row per
        # title it is a copy of and stands for each.
        .outerjoin(watched_link, col(watched_link.show_id) == col(watched_show.id))
        .join(Watch, col(Watch.canonical_episode_key) == col(watched_episode.key))
        .where(
            is_canonical(watched_episode),
            Watch.user_id == user.id,
        )
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
    watched_episode = aliased(Episode)
    last_watched = (
        select(
            col(watched_episode.id).label("canonical_episode_id"),
            func.max(
                case((col(Watch.verified).is_(True), Watch.watch_date)),
            ).label(EPISODE_LAST_WATCH_COMPLETED_COLUMN),
            func.max(
                case((col(Watch.verified).is_(False), Watch.watch_date)),
            ).label(EPISODE_LAST_WATCH_INCOMPLETE_COLUMN),
        )
        .select_from(Watch)
        .join(
            watched_episode,
            col(watched_episode.key) == col(Watch.canonical_episode_key),
        )
        .where(is_canonical(watched_episode), col(Watch.user_id) == user.id)
        .group_by(col(watched_episode.id))
        .subquery(EPISODE_LAST_WATCHED_SUBQUERY)
    )

    return query.outerjoin(
        last_watched,
        episode_id() == last_watched.c.canonical_episode_id,
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

    identifiers = [canonical_id_of(episode) for episode in episodes]
    watched_episode = aliased(Episode)
    rows = session.exec(
        select(col(watched_episode.id), Watch)  # type: ignore[call-overload]
        .join(
            watched_episode,
            col(watched_episode.key) == col(Watch.canonical_episode_key),
        )
        .where(
            is_canonical(watched_episode),
            col(watched_episode.id).in_(identifiers),
            Watch.user_id == user.id,
        )
        .order_by(
            col(watched_episode.id),
            desc(Watch.watch_date),
            desc(Watch.id),
        )
        .distinct(col(watched_episode.id)),
    ).all()

    return dict(rows)
