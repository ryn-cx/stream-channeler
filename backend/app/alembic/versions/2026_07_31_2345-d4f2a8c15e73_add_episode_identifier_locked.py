"""add episode_identifier_locked to episode

Revision ID: d4f2a8c15e73
Revises: c3a1f7d92b48
Create Date: 2026-07-31 23:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4f2a8c15e73'
down_revision = 'c3a1f7d92b48'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'episode',
        sa.Column(
            'episode_identifier_locked',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    op.drop_column('episode', 'episode_identifier_locked')
