"""Remove name requirement

Revision ID: 0d6ce5b565f0
Revises: 4fdff664024d
Create Date: 2026-03-07 19:11:20.263193

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '0d6ce5b565f0'
down_revision = '4fdff664024d'
branch_labels = None
depends_on = None


def upgrade():
    # Old PK was (user_id, name); new PK is just (id)
    op.drop_constraint('channel_pkey', 'channel', type_='primary')
    op.create_primary_key('channel_pkey', 'channel', ['id'])
    op.alter_column('channel', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)


def downgrade():
    op.alter_column('channel', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_constraint('channel_pkey', 'channel', type_='primary')
    op.create_primary_key('channel_pkey', 'channel', ['user_id', 'name'])
