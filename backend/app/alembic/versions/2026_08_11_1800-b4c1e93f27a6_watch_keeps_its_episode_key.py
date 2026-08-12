"""a watch holds the key of the episode it is of

The key is the whole of what says which episode an episode is, so a `Watch`
carries the key itself rather than only borrowing the id of the row holding it.
The row can then be deleted - by a title being reconciled, or by the cascade
from a canonical title nothing claims - and the watch survives it, dormant,
still saying what it was of and claimed back the moment that key exists again.

The pointer goes nullable and SET NULL for the same reason. A watch of a keyless
row has no key to fall back on, so it is deleted with the row it named; that is
handled in the application, since the database cannot make one foreign key
cascade for some rows and null for others.

Revision ID: b4c1e93f27a6
Revises: c5e8a2b7d914
Create Date: 2026-08-11 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4c1e93f27a6"
down_revision = "c5e8a2b7d914"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "watch",
        sa.Column("canonical_episode_key", sa.String(), nullable=True),
    )
    # No filter on the key: a watch of a keyless row lands with no key, which is
    # what "there is nothing left saying what this was of" looks like.
    op.execute(
        """
        UPDATE watch SET canonical_episode_key = canonicalepisode.key
        FROM canonicalepisode
        WHERE canonicalepisode.id = watch.canonical_episode_id
        """,  # noqa: S608 - No stored data is interpolated into this statement.
    )

    # Two rows can share a key where the same media is reached two ways, so the
    # same watch can already be recorded against both. They are one watch under
    # the key, and the older row is the one kept.
    op.execute(
        """
        DELETE FROM watch WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY user_id, canonical_episode_key, watch_date
                    ORDER BY created_at, id
                ) AS position
                FROM watch
                WHERE canonical_episode_key IS NOT NULL
            ) AS ranked
            WHERE ranked.position > 1
        )
        """,  # noqa: S608 - No stored data is interpolated into this statement.
    )

    op.alter_column(
        "watch",
        "canonical_episode_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.drop_constraint("watch_canonical_episode_id_fkey", "watch", type_="foreignkey")
    op.create_foreign_key(
        "watch_canonical_episode_id_fkey",
        "watch",
        "canonicalepisode",
        ["canonical_episode_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Partial again, as it was before the pointer was made required: a dormant
    # watch points at nothing and is held apart by its key instead.
    op.drop_index(
        "Watch-user_id-canonical_episode_id-watch_date-key",
        table_name="watch",
    )
    op.create_index(
        "Watch-user_id-canonical_episode_id-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_id", "watch_date"],
        unique=True,
        postgresql_where=sa.text("canonical_episode_id IS NOT NULL"),
    )
    op.create_index(
        "Watch-user_id-canonical_episode_key-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_key", "watch_date"],
        unique=True,
        postgresql_where=sa.text("canonical_episode_key IS NOT NULL"),
    )
    op.create_index(
        "Watch-canonical_episode_key-index",
        "watch",
        ["canonical_episode_key"],
        postgresql_where=sa.text("canonical_episode_id IS NULL"),
    )


def downgrade():
    op.drop_index("Watch-canonical_episode_key-index", table_name="watch")
    op.drop_index(
        "Watch-user_id-canonical_episode_key-watch_date-key",
        table_name="watch",
    )
    op.drop_index(
        "Watch-user_id-canonical_episode_id-watch_date-key",
        table_name="watch",
    )
    op.create_index(
        "Watch-user_id-canonical_episode_id-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_id", "watch_date"],
        unique=True,
    )

    # A dormant watch has nowhere to point once the pointer is required again.
    op.execute("DELETE FROM watch WHERE canonical_episode_id IS NULL")
    op.alter_column(
        "watch",
        "canonical_episode_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_constraint("watch_canonical_episode_id_fkey", "watch", type_="foreignkey")
    op.create_foreign_key(
        "watch_canonical_episode_id_fkey",
        "watch",
        "canonicalepisode",
        ["canonical_episode_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("watch", "canonical_episode_key")
