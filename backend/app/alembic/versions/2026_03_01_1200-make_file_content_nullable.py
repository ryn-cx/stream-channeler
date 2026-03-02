"""Make file content nullable.

Revision ID: b2f4a1c3d5e6
Revises: a1eb96f0de97
Create Date: 2026-03-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2f4a1c3d5e6'
down_revision = 'a1eb96f0de97'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('file', 'content',
               existing_type=sa.VARCHAR(),
               nullable=True)


def downgrade():
    op.alter_column('file', 'content',
               existing_type=sa.VARCHAR(),
               nullable=False)
