"""make episode_identifier required and key watches on it

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-07-21 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7d8e9f0a1b2'
down_revision = 'b6c7d8e9f0a1'
branch_labels = None
depends_on = None


def upgrade():
    # Backfill any episode that still has no identifier with its owning plugin's
    # natural identifier so the column can become non-null. Re-importing later
    # overrides TMDB-matched episodes with their "TMDB <id>" identifier.
    op.execute(
        """
        UPDATE episode AS e
        SET episode_identifier = p.key || ' ' || e.key
        FROM season AS se, show AS sh, source AS so, plugin AS p
        WHERE e.season_id = se.id
          AND se.show_id = sh.id
          AND sh.source_id = so.id
          AND so.plugin_id = p.id
          AND e.episode_identifier IS NULL
        """,
    )
    op.alter_column(
        'episode',
        'episode_identifier',
        existing_type=sa.String(),
        nullable=False,
    )

    # Move watches from a per-episode key onto episode_identifier.
    op.add_column(
        'watch',
        sa.Column('episode_identifier', sa.String(), nullable=True),
    )
    op.execute(
        """
        UPDATE watch AS w
        SET episode_identifier = e.episode_identifier
        FROM episode AS e
        WHERE w.episode_id = e.id
        """,
    )
    # Collapse the rows the old sync duplicated across sources onto one row per
    # (user, episode_identifier, watch_date).
    op.execute(
        """
        DELETE FROM watch a
        USING watch b
        WHERE a.ctid < b.ctid
          AND a.user_id = b.user_id
          AND a.episode_identifier = b.episode_identifier
          AND a.watch_date = b.watch_date
        """,
    )

    op.drop_index('Watch-user_id-episode_id-index', table_name='watch')
    op.drop_constraint('watch_pkey', 'watch', type_='primary')
    op.drop_constraint('watch_episode_id_fkey', 'watch', type_='foreignkey')
    op.drop_column('watch', 'episode_id')

    op.alter_column(
        'watch',
        'episode_identifier',
        existing_type=sa.String(),
        nullable=False,
    )
    op.create_primary_key(
        'watch_pkey',
        'watch',
        ['user_id', 'episode_identifier', 'watch_date'],
    )
    op.create_index(
        'Watch-user_id-episode_identifier-index',
        'watch',
        ['user_id', 'episode_identifier'],
        unique=False,
    )


def downgrade():
    # Best-effort reversal: map each watch back to a representative episode for its
    # identifier. The original per-source duplicate rows cannot be reconstructed.
    op.add_column('watch', sa.Column('episode_id', sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE watch AS w
        SET episode_id = (
            SELECT e.id FROM episode AS e
            WHERE e.episode_identifier = w.episode_identifier
            ORDER BY e.id
            LIMIT 1
        )
        """,
    )
    op.execute("DELETE FROM watch WHERE episode_id IS NULL")

    op.drop_index('Watch-user_id-episode_identifier-index', table_name='watch')
    op.drop_constraint('watch_pkey', 'watch', type_='primary')
    op.drop_column('watch', 'episode_identifier')

    op.alter_column('watch', 'episode_id', existing_type=sa.Uuid(), nullable=False)
    op.create_foreign_key(
        'watch_episode_id_fkey',
        'watch',
        'episode',
        ['episode_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_primary_key(
        'watch_pkey',
        'watch',
        ['user_id', 'episode_id', 'watch_date'],
    )
    op.create_index(
        'Watch-user_id-episode_id-index',
        'watch',
        ['user_id', 'episode_id'],
        unique=False,
    )

    op.alter_column(
        'episode',
        'episode_identifier',
        existing_type=sa.String(),
        nullable=True,
    )
