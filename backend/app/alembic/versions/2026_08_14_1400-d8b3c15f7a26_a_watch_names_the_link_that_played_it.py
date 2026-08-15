"""a watch names the link that played it

A watch held the identifier of the episode itself, whichever website's link had
actually played it. So a watch said what was watched but not where, and two
libraries that both carry an episode were indistinguishable once the watch was
recorded.

A watch now holds the identifier of the link it was made against, which is the
whole of what the `User` did. What it counts for is worked out on the way back
out instead: the identifier is read to whatever row carries it, and that row is
read to the episode it stands for, so a watch made on one website still marks the
episode on every other. A row that links to nothing is the episode itself and
stands for itself, so a watch of one counts where it was made.

Nothing changes for a watch left as it was: an episode's own identifier reads
back to the episode. The backfill is only so the stored rows say the same thing
the new ones do, and a watch whose link has since been deleted has no link left
to be named by, so it keeps naming the episode.

The identifier index comes off the episodes and goes across every row, since the
join now lands on links as well.

Revision ID: d8b3c15f7a26
Revises: c4f2b9e73a18
Create Date: 2026-08-14 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d8b3c15f7a26"

down_revision = "c4f2b9e73a18"
branch_labels = None
depends_on = None

_POINT_WATCHES_AT_THEIR_LINK = """
    UPDATE watch
    SET watch_identifier = episode.watch_identifier
    FROM episode
    WHERE episode.id = watch.episode_id
      AND episode.watch_identifier <> watch.watch_identifier
"""

_POINT_WATCHES_AT_THE_EPISODE = """
    UPDATE watch
    SET watch_identifier = canonical_episode.watch_identifier
    FROM episode
    JOIN episode AS canonical_episode
      ON canonical_episode.id = episode.canonical_episode_id
    WHERE episode.id = watch.episode_id
      AND canonical_episode.watch_identifier <> watch.watch_identifier
"""


def upgrade() -> None:
    op.execute(sa.text(_POINT_WATCHES_AT_THEIR_LINK))
    op.drop_index("Episode-canonical-watch_identifier-index", table_name="episode")
    op.create_index(
        "Episode-watch_identifier-index",
        "episode",
        ["watch_identifier"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("Episode-watch_identifier-index", table_name="episode")
    op.create_index(
        "Episode-canonical-watch_identifier-index",
        "episode",
        ["watch_identifier"],
        unique=False,
        postgresql_where=sa.text("canonical_episode_id IS NULL"),
    )
    op.execute(sa.text(_POINT_WATCHES_AT_THE_EPISODE))
