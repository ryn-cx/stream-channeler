# TODO: Validate
"""Reading a `Watch` back to the episode it is of.

A watch is recorded against the one link that played it and carries that link's
own identifier, not the canonical episode's. The rows it counts for are still
the whole of the media: the canonical episode and every other link to it. So a
watch is resolved by matching its identifier to whatever row carries it and
taking the canonical episode that row stands for. A row that links to nothing is
the episode itself and so stands for itself, which is what makes a watch of a
plugin nothing has been minted for count where it was made.
"""

import uuid
from collections import defaultdict
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, and_, col, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.episodes import (
    canonical_episode_id_column,
    canonical_episode_link,
    links_of,
)
from app.episodes.models import Episode
from app.watches.models import Watch


# TODO: Validate
def watch_names(
    episode: Any,  # noqa: ANN401 - A model class or an alias of one.
) -> ColumnElement[bool]:
    return or_(
        col(episode.id) == col(Watch.episode_id),
        and_(
            col(Watch.episode_id).is_(None),
            col(episode.watch_identifier) == col(Watch.watch_identifier),
        ),
    )


# TODO: Validate
def watched_canonical_ids(user_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    """Return the canonical episodes the `User` has any watch of."""
    watched_episode = aliased(Episode)
    watched_link = canonical_episode_link()
    return (
        select(canonical_episode_id_column(watched_episode, watched_link))
        .select_from(watched_episode)
        .outerjoin(watched_link, links_of(watched_episode, watched_link))
        .join(
            Watch,
            col(Watch.watch_identifier) == col(watched_episode.watch_identifier),
        )
        .where(col(Watch.user_id) == user_id)
    )


# TODO: Validate
def canonical_id_by_watch(
    session: Session,
    watches: Collection[Watch],
) -> dict[uuid.UUID, uuid.UUID]:
    if not watches:
        return {}
    named_episode = aliased(Episode)
    named_link = canonical_episode_link()
    canonical_id = canonical_episode_id_column(named_episode, named_link)
    rows = session.exec(
        select(col(Watch.id), canonical_id)
        .select_from(Watch)
        .join(named_episode, watch_names(named_episode))
        .outerjoin(named_link, links_of(named_episode, named_link))
        .where(col(Watch.id).in_({watch.id for watch in watches}))
        .order_by(col(Watch.id), canonical_id)
        .distinct(col(Watch.id)),
    ).all()
    return dict(rows)


# TODO: Validate
def watches_of_canonical_ids(
    user_id: uuid.UUID,
    canonical_ids: Collection[uuid.UUID],
) -> SelectOfScalar[Watch]:
    named_episode = aliased(Episode)
    named_link = canonical_episode_link()
    return (
        select(Watch)
        .join(
            named_episode,
            col(named_episode.watch_identifier) == col(Watch.watch_identifier),
        )
        .outerjoin(named_link, links_of(named_episode, named_link))
        .where(
            col(Watch.user_id) == user_id,
            canonical_episode_id_column(named_episode, named_link).in_(
                set(canonical_ids),
            ),
        )
    )


# TODO: Validate
def watched_dates_by_canonical_id(
    session: Session,
    user_id: uuid.UUID,
    canonical_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, list[datetime]]:
    """Return the `User`'s watch dates for each of `canonical_ids`.

    Every link to the episode answers for it, so a date recorded against one
    website's link is a date the episode was watched on wherever it is asked
    about.
    """
    if not canonical_ids:
        return {}
    watched_episode = aliased(Episode)
    watched_link = canonical_episode_link()
    canonical_id = canonical_episode_id_column(watched_episode, watched_link)
    rows = session.exec(
        select(canonical_id, Watch.watch_date)
        .select_from(watched_episode)
        .outerjoin(watched_link, links_of(watched_episode, watched_link))
        .join(
            Watch,
            col(Watch.watch_identifier) == col(watched_episode.watch_identifier),
        )
        .where(
            col(Watch.user_id) == user_id,
            canonical_id.in_(set(canonical_ids)),
        ),
    ).all()
    watched_dates: dict[uuid.UUID, list[datetime]] = defaultdict(list)
    for canonical_id, watch_date in rows:
        watched_dates[canonical_id].append(watch_date)
    return watched_dates
