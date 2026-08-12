"""a show is a copy of every title it mixes

A website's listing was a copy of one title, and a service that files two titles
under one listing - a YouTube channel whose uploads are two series, a sequel sold
as another season - had to be one or the other. Which titles a copy stands for is
now a table of its own, so it can be both.

The title already on a copy is written in as one of them, and so is the title of
every season under it, which is where a listing that mixes titles says so.

Revision ID: f3c8d5b2a417
Revises: e7b3d1a9c206
Create Date: 2026-08-12 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f3c8d5b2a417"
down_revision = "e7b3d1a9c206"
branch_labels = None
depends_on = None

# The title a copy carries, and the title of every season under it. A season the
# TMDB linker put under another title is the whole of what says a listing mixes
# titles, so the two together are every title a copy stands for.
_BACKFILL = """
    INSERT INTO showcanonicalshow (id, created_at, modified_at, show_id,
                                   canonical_show_id)
    SELECT gen_random_uuid(), now(), now(), title.show_id, title.canonical_show_id
    FROM (
        SELECT show.id AS show_id, show.canonical_show_id AS canonical_show_id
        FROM show
        UNION
        SELECT season.show_id AS show_id,
               canonicalseason.canonical_show_id AS canonical_show_id
        FROM season
        JOIN canonicalseason ON canonicalseason.id = season.canonical_season_id
    ) AS title
"""


def upgrade():
    op.create_table(
        "showcanonicalshow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("show_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_show_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["show_id"], ["show.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["canonical_show_id"],
            ["canonicalshow.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("show_id", "canonical_show_id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(
        "ShowCanonicalShow-canonical_show_id-index",
        "showcanonicalshow",
        ["canonical_show_id"],
    )
    op.execute(_BACKFILL)


def downgrade():
    op.drop_index("ShowCanonicalShow-canonical_show_id-index", "showcanonicalshow")
    op.drop_table("showcanonicalshow")
