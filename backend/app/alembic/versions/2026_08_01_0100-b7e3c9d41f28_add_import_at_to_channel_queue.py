"""add import_at to channelqueue

Revision ID: b7e3c9d41f28
Revises: d4f2a8c15e73
Create Date: 2026-08-01 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7e3c9d41f28'
down_revision = 'd4f2a8c15e73'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'channelqueue',
        sa.Column('import_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('channelqueue', 'import_at')
