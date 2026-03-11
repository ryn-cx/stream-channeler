"""add_public_to_plugin

Revision ID: 9b5aec704c56
Revises: 0d6ce5b565f0
Create Date: 2026-03-08 19:23:45.994428

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9b5aec704c56'
down_revision = '0d6ce5b565f0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plugin', sa.Column('public', sa.Boolean(), nullable=True))
    op.execute("UPDATE plugin SET public = false WHERE public IS NULL")
    op.alter_column('plugin', 'public', nullable=False)


def downgrade():
    op.drop_column('plugin', 'public')
