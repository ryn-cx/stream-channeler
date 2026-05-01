"""rename whitelist tables to filter

Revision ID: 51c2001ab376
Revises: a17767a2d057
Create Date: 2026-05-01 03:17:28.261296

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '51c2001ab376'
down_revision = 'a17767a2d057'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('channelseasonwhitelist', 'channelseasonfilter')
    op.execute(
        'ALTER INDEX "ChannelSeasonWhiteList-season_id-index" '
        'RENAME TO "ChannelSeasonFilter-season_id-index"',
    )
    op.rename_table('channelepisodewhitelist', 'channelepisodefilter')
    op.execute(
        'ALTER INDEX "ChannelEpisodeWhiteList-episode_id-index" '
        'RENAME TO "ChannelEpisodeFilter-episode_id-index"',
    )


def downgrade():
    op.execute(
        'ALTER INDEX "ChannelEpisodeFilter-episode_id-index" '
        'RENAME TO "ChannelEpisodeWhiteList-episode_id-index"',
    )
    op.rename_table('channelepisodefilter', 'channelepisodewhitelist')
    op.execute(
        'ALTER INDEX "ChannelSeasonFilter-season_id-index" '
        'RENAME TO "ChannelSeasonWhiteList-season_id-index"',
    )
    op.rename_table('channelseasonfilter', 'channelseasonwhitelist')
