"""detach watches from deleted episodes

Revision ID: a1c4e7b93d52
Revises: b7e3c9d41f28
Create Date: 2026-08-06 06:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "a1c4e7b93d52"
down_revision = "b7e3c9d41f28"
branch_labels = None
depends_on = None


def upgrade():
    # A watch only knew what it watched by way of its episode, so deleting the
    # episode took the watch with it. The identifier moves onto the watch so the
    # row can outlive the episode and be relinked later.
    op.add_column(
        "watch",
        sa.Column(
            "episode_identifier", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.execute(
        """
        UPDATE watch
        SET episode_identifier = episode.episode_identifier
        FROM episode
        WHERE episode.id = watch.episode_id
        """
    )
    # Every existing row has an episode, so nothing should be left unset.
    op.alter_column(
        "watch",
        "episode_identifier",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )

    # The identifier is what makes a watch unique now, so the key no longer
    # depends on a column that is about to become nullable. Collapse the rows
    # that different episodes sharing an identifier could have produced.
    op.execute(
        """
        DELETE FROM watch AS duplicate
        USING watch AS kept
        WHERE duplicate.user_id = kept.user_id
          AND duplicate.episode_identifier = kept.episode_identifier
          AND duplicate.watch_date = kept.watch_date
          AND duplicate.id > kept.id
        """
    )
    op.drop_constraint("watch_pkey", "watch", type_="primary")
    op.create_primary_key("watch_pkey", "watch", ["id"])
    op.create_unique_constraint(
        "Watch-user_id-episode_identifier-watch_date-key",
        "watch",
        ["user_id", "episode_identifier", "watch_date"],
    )
    op.create_index(
        "Watch-episode_identifier-index", "watch", ["episode_identifier"], unique=False
    )

    # Deleting an episode now detaches its watches instead of deleting them.
    op.drop_constraint("watch_episode_id_fkey", "watch", type_="foreignkey")
    op.alter_column("watch", "episode_id", existing_type=sa.Uuid(), nullable=True)
    op.create_foreign_key(
        "watch_episode_id_fkey",
        "watch",
        "episode",
        ["episode_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    # A detached watch has no episode to point at and cannot be represented by
    # the old key, so those rows go.
    op.execute("DELETE FROM watch WHERE episode_id IS NULL")

    op.drop_constraint("watch_episode_id_fkey", "watch", type_="foreignkey")
    op.alter_column("watch", "episode_id", existing_type=sa.Uuid(), nullable=False)
    op.create_foreign_key(
        "watch_episode_id_fkey",
        "watch",
        "episode",
        ["episode_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("Watch-episode_identifier-index", table_name="watch")
    op.drop_constraint(
        "Watch-user_id-episode_identifier-watch_date-key", "watch", type_="unique"
    )
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
    op.drop_constraint("watch_pkey", "watch", type_="primary")
    op.create_primary_key(
        "watch_pkey", "watch", ["user_id", "episode_id", "watch_date"]
    )

    op.drop_column("watch", "episode_identifier")
