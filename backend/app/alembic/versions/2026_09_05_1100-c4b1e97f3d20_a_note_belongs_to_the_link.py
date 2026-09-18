# TODO: Validate
"""a note belongs to the link

Revision ID: c4b1e97f3d20
Revises: a2e8d47c9b13
Create Date: 2026-09-05 11:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "c4b1e97f3d20"
down_revision = "a2e8d47c9b13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "episodecanonicalepisode",
        sa.Column("note", sa.String(), nullable=True),
    )
    op.execute(
        """
        UPDATE episodecanonicalepisode AS link
        SET note = episode.canonical_episode_note
        FROM episode
        WHERE episode.id = link.episode_id
        """,
    )
    op.drop_column("episode", "canonical_episode_note")


def downgrade() -> None:
    op.add_column(
        "episode",
        sa.Column("canonical_episode_note", sa.String(), nullable=True),
    )
    op.execute(
        """
        UPDATE episode
        SET canonical_episode_note = notes.note
        FROM (
            SELECT episode_id, MIN(note) AS note
            FROM episodecanonicalepisode
            WHERE note IS NOT NULL
            GROUP BY episode_id
        ) AS notes
        WHERE episode.id = notes.episode_id
        """,
    )
    op.drop_column("episodecanonicalepisode", "note")
