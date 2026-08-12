"""an episode is dated by when it aired and nothing else

`release_date` never held anything worth reading. Websites filled it with
whatever date they had to hand - when a listing was published, when a licence
started, when a file was uploaded - so two copies of one episode disagreed about
it for reasons that had nothing to do with the episode. `air_date` is the date
the episode itself has, so it is the only one kept.

The copies whose release date was the only date they carried have it read across
to `air_date` before the column goes, since that is the date those plugins were
reporting all along.

Revision ID: b8f4d3e6c729
Revises: a7e2c9b4f318
Create Date: 2026-08-12 11:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8f4d3e6c729"
down_revision = "a7e2c9b4f318"
branch_labels = None
depends_on = None

# A row with no air date and a release date was one of the copies whose plugin
# only ever reported the one date.
_KEEP_THE_ONLY_DATE = """
    UPDATE {table}
    SET air_date = release_date
    WHERE air_date IS NULL AND release_date IS NOT NULL
"""


def upgrade():
    for table in ("episode", "canonicalepisode"):
        op.execute(_KEEP_THE_ONLY_DATE.format(table=table))
    op.drop_index("Episode-release_date-index", "episode")
    op.drop_index("CanonicalEpisode-release_date-index", "canonicalepisode")
    op.drop_column("episode", "release_date")
    op.drop_column("canonicalepisode", "release_date")


def downgrade():
    op.add_column(
        "episode",
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "canonicalepisode",
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("Episode-release_date-index", "episode", ["release_date"])
    op.create_index(
        "CanonicalEpisode-release_date-index",
        "canonicalepisode",
        ["release_date"],
    )
