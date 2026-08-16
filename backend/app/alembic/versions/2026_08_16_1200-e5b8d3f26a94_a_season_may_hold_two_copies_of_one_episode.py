"""a season may hold two copies of one episode

A copy of a season was allowed to name each episode once, which reads as a rule
about the media and is really a rule about one website's listing. A website is
free to list the same episode twice: Hulu carries a dubbed row and a subtitled
row of every episode of a title, and both of them are that episode, so pointing
them at it is the right answer rather than the collision the database took it
for.

The index stays, since looking a season's copies up by the episode they stand
for is still worth an index. Only the uniqueness goes.

Revision ID: e5b8d3f26a94
Revises: d4a7c2e91b63
Create Date: 2026-08-16 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5b8d3f26a94"
down_revision = "d4a7c2e91b63"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "Episode-live-season_id-canonical_episode_id-key",
        table_name="episode",
    )
    op.execute(
        'CREATE INDEX "Episode-live-season_id-canonical_episode_id-key"'
        " ON episode (season_id, canonical_episode_id)"
        " WHERE deleted_at IS NULL AND canonical_episode_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index(
        "Episode-live-season_id-canonical_episode_id-key",
        table_name="episode",
    )
    op.execute(
        'CREATE UNIQUE INDEX "Episode-live-season_id-canonical_episode_id-key"'
        " ON episode (season_id, canonical_episode_id)"
        " WHERE deleted_at IS NULL AND canonical_episode_id IS NOT NULL",
    )
