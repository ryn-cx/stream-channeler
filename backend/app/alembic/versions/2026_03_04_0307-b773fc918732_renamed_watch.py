"""Renamed Watch

Revision ID: b773fc918732
Revises: e7911746fbdc
Create Date: 2026-03-04 03:07:19.266919

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b773fc918732'
down_revision = 'e7911746fbdc'
branch_labels = None
depends_on = None


def upgrade():
    # Rename table
    op.rename_table('episodewatch', 'watch')

    # Rename indexes
    op.drop_index('EpisodeWatch-user_id-episode_id-index', table_name='watch')
    op.drop_index('EpisodeWatch-user_id-verified-index', table_name='watch')
    op.drop_index('EpisodeWatch-watch_date-index', table_name='watch')
    op.create_index('Watch-user_id-episode_id-index', 'watch', ['user_id', 'episode_id'])
    op.create_index('Watch-user_id-verified-index', 'watch', ['user_id', 'verified'])
    op.create_index('Watch-watch_date-index', 'watch', ['watch_date'])


def downgrade():
    # Rename indexes back
    op.drop_index('Watch-user_id-episode_id-index', table_name='watch')
    op.drop_index('Watch-user_id-verified-index', table_name='watch')
    op.drop_index('Watch-watch_date-index', table_name='watch')
    op.create_index('EpisodeWatch-user_id-episode_id-index', 'watch', ['user_id', 'episode_id'])
    op.create_index('EpisodeWatch-user_id-verified-index', 'watch', ['user_id', 'verified'])
    op.create_index('EpisodeWatch-watch_date-index', 'watch', ['watch_date'])

    # Rename table back
    op.rename_table('watch', 'episodewatch')
