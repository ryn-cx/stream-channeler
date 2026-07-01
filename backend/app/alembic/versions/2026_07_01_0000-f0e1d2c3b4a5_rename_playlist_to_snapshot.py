"""rename playlist to snapshot

Revision ID: f0e1d2c3b4a5
Revises: c4d5e6f7a8b9
Create Date: 2026-07-01 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f0e1d2c3b4a5'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('playlist', 'snapshot')
    op.rename_table('playlistepisode', 'snapshotepisode')
    op.alter_column('snapshotepisode', 'playlist_id', new_column_name='snapshot_id')
    op.execute(
        'ALTER INDEX "Playlist-user_id-index" RENAME TO "Snapshot-user_id-index"',
    )
    op.execute(
        'ALTER INDEX "PlaylistEpisode-episode_id-index" '
        'RENAME TO "SnapshotEpisode-episode_id-index"',
    )


def downgrade():
    op.execute(
        'ALTER INDEX "SnapshotEpisode-episode_id-index" '
        'RENAME TO "PlaylistEpisode-episode_id-index"',
    )
    op.execute(
        'ALTER INDEX "Snapshot-user_id-index" RENAME TO "Playlist-user_id-index"',
    )
    op.alter_column('snapshotepisode', 'snapshot_id', new_column_name='playlist_id')
    op.rename_table('snapshotepisode', 'playlistepisode')
    op.rename_table('snapshot', 'playlist')
