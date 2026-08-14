# TODO: Validate
"""The canonical rows the episode query is built around, as one set of entities.

The query reaches each level's canonical row once and several modules read off
it - the filters, the sort expressions, the dedup ranking and the column
fallbacks - so they all have to name the same entity or the query would join a
level twice and read one of the two at random.

They are aliased rather than named directly so that reaching a level twice is
always something the query says out loud. A canonical row and a non-canonical one are
the same shape, and a query that names both without aliasing either has nothing
to tell them apart by.

Only the main episode query uses these. A query built on its own - a subquery
that is materialised before it is joined, a lookup that stands alone - has its
own scope and aliases its own entities, since sharing these would let the two
scopes correlate.
"""

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement

from app.canonical_media.filters import canonical_id_column
from app.canonical_media.seasons import season_id_column
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show

CANONICAL_EPISODE = aliased(Episode)
CANONICAL_SEASON = aliased(Season)
CANONICAL_SHOW = aliased(Show)


# TODO: Validate
def episode_id() -> ColumnElement[UUID]:
    """Return the episode a row stands for, which is the row where it is canonical.

    A website carries episodes the canonical show has no record of, so nothing
    was ever minted for them to stand for and they are the episode themselves.
    They are still episodes of the canonical show the website's row is linked to,
    so everything
    keyed by the canonical episode reads this rather than the pointer.
    """
    return canonical_id_column(Episode)


# TODO: Validate
def season_id() -> ColumnElement[UUID]:
    """Return the season a row belongs to, which is its own where it has no canonical."""
    return season_id_column(Episode, CANONICAL_EPISODE)
