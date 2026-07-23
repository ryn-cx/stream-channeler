"""rekey watch on episode_identifier

Revision ID: d8e9f0a1b2c3
Revises: b6c7d8e9f0a1
Create Date: 2026-07-21 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8e9f0a1b2c3'
down_revision = 'b6c7d8e9f0a1'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM episode WHERE episode_identifier IS NULL")
    op.alter_column(
        'episode',
        'episode_identifier',
        existing_type=sa.String(),
        nullable=False,
    )

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
    op.execute(
        """
        DELETE FROM watch
        WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY user_id, episode_identifier, watch_date
                    ORDER BY verified DESC, created_at
                ) AS row_number
                FROM watch
            ) AS ranked
            WHERE row_number > 1
        )
        """,
    )

    op.drop_index('Watch-user_id-episode_id-index', table_name='watch')
    # Databases created from the squashed initial migration name these
    # constraints `watch_*`; databases that predate the `episodewatch` -> `watch`
    # table rename keep the old `episodewatch_*` names. Drop whichever exists.
    op.execute(
        'ALTER TABLE watch DROP CONSTRAINT IF EXISTS episodewatch_episode_id_fkey',
    )
    op.execute(
        'ALTER TABLE watch DROP CONSTRAINT IF EXISTS watch_episode_id_fkey',
    )
    op.execute('ALTER TABLE watch DROP CONSTRAINT IF EXISTS episodewatch_pkey')
    op.execute('ALTER TABLE watch DROP CONSTRAINT IF EXISTS watch_pkey')
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
        'episodewatch_episode_id_fkey',
        'watch',
        'episode',
        ['episode_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_primary_key(
        'episodewatch_pkey',
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
