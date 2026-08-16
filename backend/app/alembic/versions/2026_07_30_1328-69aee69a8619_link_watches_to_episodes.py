"""link watches to episodes

Revision ID: 69aee69a8619
Revises: bbc24e1b5276
Create Date: 2026-07-30 13:28:18.661617

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "69aee69a8619"
down_revision = "bbc24e1b5276"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("watch", sa.Column("episode_id", sa.Uuid(), nullable=True))

    # A watch used to name an identifier rather than an episode, and an identifier can
    # resolve to an episode in every source, so point each watch at the lowest id among
    # the episodes sharing its identifier. Which one is chosen does not change what the
    # user sees because reads still group watches by that episode's identifier.
    op.execute(
        """
        UPDATE watch AS target
        SET episode_id = chosen.id
        FROM (
            SELECT DISTINCT ON (episode_identifier) episode_identifier, id
            FROM episode
            WHERE deleted_at IS NULL
            ORDER BY episode_identifier, id
        ) AS chosen
        WHERE chosen.episode_identifier = target.episode_identifier
        """
    )
    # An identifier that no longer resolves to an episode cannot be represented by a
    # foreign key, so those watches are dropped.
    op.execute("DELETE FROM watch WHERE episode_id IS NULL")
    # Watches for different episodes that shared an identifier collapse onto the same
    # episode, so keep one row per new primary key.
    op.execute(
        """
        DELETE FROM watch AS duplicate
        USING watch AS kept
        WHERE duplicate.user_id = kept.user_id
          AND duplicate.episode_id = kept.episode_id
          AND duplicate.watch_date = kept.watch_date
          AND duplicate.id > kept.id
        """
    )

    op.alter_column("watch", "episode_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("watch_pkey", "watch", type_="primary")
    op.create_primary_key(
        "watch_pkey", "watch", ["user_id", "episode_id", "watch_date"]
    )
    op.create_foreign_key(
        "watch_episode_id_fkey",
        "watch",
        "episode",
        ["episode_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("Watch-episode_id-index", "watch", ["episode_id"], unique=False)
    op.create_index(
        "Watch-user_id-episode_id-index",
        "watch",
        ["user_id", "episode_id"],
        unique=False,
    )
    op.drop_index("Watch-episode_identifier-index", table_name="watch")
    op.drop_index("Watch-user_id-episode_identifier-index", table_name="watch")
    op.drop_column("watch", "episode_identifier")


def downgrade():
    op.add_column(
        "watch",
        sa.Column(
            "episode_identifier", sa.VARCHAR(), autoincrement=False, nullable=True
        ),
    )
    op.execute(
        """
        UPDATE watch AS target
        SET episode_identifier = episode.episode_identifier
        FROM episode
        WHERE episode.id = target.episode_id
        """
    )
    op.alter_column(
        "watch", "episode_identifier", existing_type=sa.VARCHAR(), nullable=False
    )
    op.create_index(
        "Watch-user_id-episode_identifier-index",
        "watch",
        ["user_id", "episode_identifier"],
        unique=False,
    )
    op.create_index(
        "Watch-episode_identifier-index", "watch", ["episode_identifier"], unique=False
    )
    op.drop_index("Watch-user_id-episode_id-index", table_name="watch")
    op.drop_index("Watch-episode_id-index", table_name="watch")
    op.drop_constraint("watch_episode_id_fkey", "watch", type_="foreignkey")
    op.drop_constraint("watch_pkey", "watch", type_="primary")
    op.create_primary_key(
        "watch_pkey", "watch", ["user_id", "episode_identifier", "watch_date"]
    )
    op.drop_column("watch", "episode_id")
