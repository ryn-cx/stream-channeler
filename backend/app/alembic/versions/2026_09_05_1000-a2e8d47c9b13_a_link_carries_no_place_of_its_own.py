"""a link carries no place of its own

`EpisodeCanonicalEpisode.sort_order` was written as a copy of the non-canonical
row's own `sort_order` and never diverged from it, and nothing ordered by it.
The row's own column is the whole of the answer.

Revision ID: a2e8d47c9b13
Revises: f0d6b83e4a71
Create Date: 2026-09-05 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "a2e8d47c9b13"
down_revision = "f0d6b83e4a71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("episodecanonicalepisode", "sort_order")


def downgrade() -> None:
    op.add_column(
        "episodecanonicalepisode",
        sa.Column("sort_order", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE episodecanonicalepisode AS link
        SET sort_order = episode.sort_order
        FROM episode
        WHERE episode.id = link.episode_id
        """,
    )
