"""index episode_identifier

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-07-21 05:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e9f0a1b2c3d4'
down_revision = 'd8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'Episode-episode_identifier-index',
        'episode',
        ['episode_identifier', 'id'],
        unique=False,
    )


def downgrade():
    op.drop_index('Episode-episode_identifier-index', table_name='episode')
