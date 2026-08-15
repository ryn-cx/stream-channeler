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

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.filters import canonical_id_column
from app.episodes.models import Episode
from app.watches.models import Watch


# TODO: Validate
def watched_canonical_ids(user_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    """The canonical episodes the `User` has any watch of."""
    watched_episode = aliased(Episode)
    return (
        select(canonical_id_column(watched_episode))
        .join(
            Watch,
            col(Watch.watch_identifier) == col(watched_episode.watch_identifier),
        )
        .where(col(Watch.user_id) == user_id)
    )


# TODO: Validate
def canonical_id_by_identifier(
    session: Session,
    watch_identifiers: Collection[str],
) -> dict[str, uuid.UUID]:
    """The canonical episode each of `watch_identifiers` names."""
    if not watch_identifiers:
        return {}
    rows = session.exec(
        select(col(Episode.watch_identifier), canonical_id_column(Episode))
        .where(col(Episode.watch_identifier).in_(set(watch_identifiers)))
        .distinct(),
    ).all()
    return dict(rows)


# TODO: Validate
def identifiers_of_canonical_ids(
    session: Session,
    canonical_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, list[str]]:
    """Every identifier a watch of each of `canonical_ids` can carry."""
    if not canonical_ids:
        return {}
    wanted = set(canonical_ids)
    rows = session.exec(
        select(canonical_id_column(Episode), col(Episode.watch_identifier)).where(
            or_(
                col(Episode.id).in_(wanted),
                col(Episode.canonical_episode_id).in_(wanted),
            ),
        ),
    ).all()
    identifiers: dict[uuid.UUID, list[str]] = defaultdict(list)
    for canonical_id, watch_identifier in rows:
        identifiers[canonical_id].append(watch_identifier)
    return identifiers


# TODO: Validate
def watched_dates_by_canonical_id(
    session: Session,
    user_id: uuid.UUID,
    canonical_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, list[datetime]]:
    """The `User`'s watch dates for each of `canonical_ids`.

    Every link to the episode answers for it, so a date recorded against one
    website's link is a date the episode was watched on wherever it is asked
    about.
    """
    if not canonical_ids:
        return {}
    watched_episode = aliased(Episode)
    rows = session.exec(
        select(canonical_id_column(watched_episode), Watch.watch_date)
        .join(
            Watch,
            col(Watch.watch_identifier) == col(watched_episode.watch_identifier),
        )
        .where(
            col(Watch.user_id) == user_id,
            canonical_id_column(watched_episode).in_(set(canonical_ids)),
        ),
    ).all()
    watched_dates: dict[uuid.UUID, list[datetime]] = defaultdict(list)
    for canonical_id, watch_date in rows:
        watched_dates[canonical_id].append(watch_date)
    return watched_dates
