# TODO: Validate


"""Which TMDB episode an `Episode` is linked to, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever one
a `User` picks.
"""

import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import nullslast
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, and_, col, func, select

from app.episodes.models import (
    Episode,
)
from app.seasons.models import Season

# An unnumbered season or episode is ordered after every numbered one.
_UNNUMBERED = float("inf")


type Numbering = tuple[uuid.UUID, int | None, int | None]


# TODO: Validate
def order(
    season_number: int | None,
    episode_number: int | None,
) -> tuple[float, float]:
    return (
        _UNNUMBERED if season_number is None else season_number,
        _UNNUMBERED if episode_number is None else episode_number,
    )


# TODO: Validate
def absolute_numbers(numberings: Sequence[Numbering]) -> dict[uuid.UUID, int]:
    """Count every episode of one title from its first, and return that count by id.

    A website that numbers a title straight through names an episode by how far
    into the title it is rather than by how far into its own season, which is
    what makes the same episode `S3E2` on one site and `27` on another. Specials
    are outside the count, since a title's own episodes are what the count runs
    over, so they are left with no number rather than given one.
    """
    ordered = sorted(
        numberings,
        key=lambda numbering: (
            *order(numbering[1], numbering[2]),
            numbering[0].bytes,
        ),
    )
    numbers: dict[uuid.UUID, int] = {}
    for record_id, season_number, _episode_number in ordered:
        if not season_number:
            continue
        numbers[record_id] = len(numbers) + 1
    return numbers


# TODO: Validate
def _counted_episodes() -> ColumnElement[bool]:
    """Which of a title's episodes the count runs over.

    A season nothing numbered and season zero are both outside it, so a special
    is left with no number rather than given one and does not push the episode
    after it along.
    """
    return and_(
        col(Episode.deleted_at).is_(None),
        col(Season.deleted_at).is_(None),
        col(Season.season_number).is_not(None),
        col(Season.season_number) != 0,
    )


# TODO: Validate
def _absolute_number_column() -> ColumnElement[int]:
    """Count each title through from its first episode.

    `nullslast` is what Postgres does with an ascending sort anyway, said outright
    because it is what stands in for `_UNNUMBERED`, and the id is what separates two
    episodes a website gave the very same numbering.
    """
    return func.row_number().over(
        partition_by=col(Season.title_id),
        order_by=(
            col(Season.season_number),
            nullslast(col(Episode.episode_number)),
            col(Episode.id),
        ),
    )


# TODO: Validate
def absolute_numbers_of(
    session: Session,
    title_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, int]:
    """Count every episode of each title, and return that count by episode id.

    The whole title is counted rather than only the episodes being listed, since an
    episode's place in a title is decided by how many come before it, which the
    ones left over from a name match say nothing about. Nothing says which rows are
    canonical, so a website's own title and a canonical title are both counted the
    way the title they are counts.
    """
    if not title_ids:
        return {}

    statement = (
        select(Episode.id, _absolute_number_column())
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(col(Season.title_id).in_(title_ids), _counted_episodes())
    )
    return dict(session.exec(statement).all())
