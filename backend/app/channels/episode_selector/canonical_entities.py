# TODO: Validate
"""The canonical rows the episode query is built around, as one set of entities.

The query reaches each level's canonical row once and several modules read off
it - the filters, the sort expressions, the dedup ranking and the column
fallbacks - so they all have to name the same entity or the query would join a
level twice and read one of the two at random.

They are aliased rather than named directly so that reaching a level twice is
always something the query says out loud. A canonical row and a copy of one are
the same shape, and a query that names both without aliasing either has nothing
to tell them apart by.

Only the main episode query uses these. A query built on its own - a subquery
that is materialised before it is joined, a lookup that stands alone - has its
own scope and aliases its own entities, since sharing these would let the two
scopes correlate.
"""

from sqlalchemy.orm import aliased

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show

CANONICAL_EPISODE = aliased(Episode)
CANONICAL_SEASON = aliased(Season)
CANONICAL_SHOW = aliased(Show)
