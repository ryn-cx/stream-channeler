"""a show carries the year it came out

TMDB is searched under a title's name, and a name on its own matches every
remake and every unrelated title that happens to share it. The year narrows
that, and it is the website that knows it, so it is stored on the copy rather
than worked out again every time a search is made.

The canonical row carries it too, since a copy's metadata is written onto the
row it stands for and the year is part of what describes a title.

A website that says nothing about when its titles came out leaves the column
empty, which is the same as it was before this: a search on the name alone.

Revision ID: d1b6f8c3e492
Revises: c9a5e7d3b184
Create Date: 2026-08-12 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1b6f8c3e492"
down_revision = "c9a5e7d3b184"
branch_labels = None
depends_on = None

_TABLES = ("show", "canonicalshow")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("year", sa.Integer(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "year")
