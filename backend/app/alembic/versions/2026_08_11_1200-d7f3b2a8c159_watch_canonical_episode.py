"""record a watch against the canonical episode it is of

A `Watch` names what was watched by its `episode_identifier`, a string that has
to be resolved through the episodes carrying it before it means anything. The
canonical episode is that meaning made into a row, so the watch points at it
directly and keeps doing so after every copy of the episode is gone.

The identifier is left in place and the pointer stays nullable: an episode that
has not been reconciled yet has no canonical row to hand over, and the code
writing identifiers has not been changed over. A later revision makes the
pointer required and drops the identifier.

Revision ID: d7f3b2a8c159
Revises: b6d2f4a9c317
Create Date: 2026-08-11 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d7f3b2a8c159"
down_revision = "b6d2f4a9c317"
branch_labels = None
depends_on = None


def upgrade():
    # RESTRICT rather than CASCADE: watch history is the reason a canonical row
    # outlives its copies, so a row a watch names is one nothing may delete.
    op.add_column("watch", sa.Column("canonical_episode_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "watch_canonical_episode_id_fkey",
        "watch",
        "canonicalepisode",
        ["canonical_episode_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Every episode sharing an identifier was given the same canonical row by the
    # previous revision, so which of them answers for it does not matter; DISTINCT
    # ON is only there to make the join one-to-one. Soft-deleted episodes count,
    # since a watch outliving its episode is the case this most needs to resolve.
    op.execute(
        """
        UPDATE watch SET canonical_episode_id = resolved.canonical_episode_id
        FROM (
            SELECT DISTINCT ON (episode.episode_identifier)
                episode.episode_identifier, episode.canonical_episode_id
            FROM episode
            WHERE episode.canonical_episode_id IS NOT NULL
            ORDER BY episode.episode_identifier, episode.id
        ) AS resolved
        WHERE resolved.episode_identifier = watch.episode_identifier
        """,  # noqa: S608 - No stored data is interpolated into this statement.
    )

    op.create_index(
        "Watch-canonical_episode_id-index",
        "watch",
        ["canonical_episode_id"],
    )
    # Partial, because a watch naming an identifier no episode carries has no
    # canonical row yet and Postgres would otherwise let those rows duplicate
    # freely. The identifier's own unique constraint still holds them apart.
    op.create_index(
        "Watch-user_id-canonical_episode_id-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_id", "watch_date"],
        unique=True,
        postgresql_where=sa.text("canonical_episode_id IS NOT NULL"),
    )


def downgrade():
    op.drop_index("Watch-user_id-canonical_episode_id-watch_date-key", table_name="watch")
    op.drop_index("Watch-canonical_episode_id-index", table_name="watch")
    op.drop_constraint("watch_canonical_episode_id_fkey", "watch", type_="foreignkey")
    op.drop_column("watch", "canonical_episode_id")
