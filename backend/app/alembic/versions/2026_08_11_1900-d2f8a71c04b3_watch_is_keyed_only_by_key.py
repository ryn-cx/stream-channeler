"""the key is the only thing a watch names an episode by

The pointer was the link and the key was the fallback; the key is the link now.
Two rows carrying one key are two ways of reaching the same media, so a watch
holding that key is a watch of both, which the pointer could never say. Nothing
is left to null out when a row goes, and nothing to claim back when it returns.

A watch of a keyless row named a stub the flush hook minted and nothing else, so
those rows are dropped rather than carried as watches of nothing.

Revision ID: d2f8a71c04b3
Revises: b4c1e93f27a6
Create Date: 2026-08-11 19:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d2f8a71c04b3"
down_revision = "b4c1e93f27a6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM watch WHERE canonical_episode_key IS NULL")
    op.alter_column(
        "watch",
        "canonical_episode_key",
        existing_type=sa.String(),
        nullable=False,
    )

    op.drop_index("Watch-canonical_episode_key-index", table_name="watch")
    op.create_index(
        "Watch-canonical_episode_key-index",
        "watch",
        ["canonical_episode_key"],
    )
    op.drop_index(
        "Watch-user_id-canonical_episode_key-watch_date-key",
        table_name="watch",
    )
    op.create_index(
        "Watch-user_id-canonical_episode_key-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_key", "watch_date"],
        unique=True,
    )

    op.drop_index(
        "Watch-user_id-canonical_episode_id-watch_date-key",
        table_name="watch",
    )
    op.drop_constraint("watch_canonical_episode_id_fkey", "watch", type_="foreignkey")
    op.drop_column("watch", "canonical_episode_id")


def downgrade():
    op.add_column("watch", sa.Column("canonical_episode_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "watch_canonical_episode_id_fkey",
        "watch",
        "canonicalepisode",
        ["canonical_episode_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # One row per key, since the pointer cannot say what carrying a key twice
    # said; the lowest id answers for it, as the forward dedupe chose.
    op.execute(
        """
        UPDATE watch SET canonical_episode_id = resolved.id
        FROM (
            SELECT DISTINCT ON (key) key, id FROM canonicalepisode
            WHERE key IS NOT NULL ORDER BY key, id
        ) AS resolved
        WHERE resolved.key = watch.canonical_episode_key
        """,  # noqa: S608 - No stored data is interpolated into this statement.
    )
    op.create_index(
        "Watch-user_id-canonical_episode_id-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_id", "watch_date"],
        unique=True,
        postgresql_where=sa.text("canonical_episode_id IS NOT NULL"),
    )

    op.drop_index(
        "Watch-user_id-canonical_episode_key-watch_date-key",
        table_name="watch",
    )
    op.create_index(
        "Watch-user_id-canonical_episode_key-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_key", "watch_date"],
        unique=True,
        postgresql_where=sa.text("canonical_episode_key IS NOT NULL"),
    )
    op.alter_column(
        "watch",
        "canonical_episode_key",
        existing_type=sa.String(),
        nullable=True,
    )
    op.drop_index("Watch-canonical_episode_key-index", table_name="watch")
    op.create_index(
        "Watch-canonical_episode_key-index",
        "watch",
        ["canonical_episode_key"],
        postgresql_where=sa.text("canonical_episode_id IS NULL"),
    )
