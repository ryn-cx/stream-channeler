"""add channel and channel order favorites

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('channelfavorite',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('channel_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'channel_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelFavorite-channel_id-index', 'channelfavorite', ['channel_id'], unique=False)
    op.create_table('channelorderfavorite',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('channel_order_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_order_id'], ['channelorder.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'channel_order_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelOrderFavorite-channel_order_id-index', 'channelorderfavorite', ['channel_order_id'], unique=False)


def downgrade():
    op.drop_index('ChannelOrderFavorite-channel_order_id-index', table_name='channelorderfavorite')
    op.drop_table('channelorderfavorite')
    op.drop_index('ChannelFavorite-channel_id-index', table_name='channelfavorite')
    op.drop_table('channelfavorite')
