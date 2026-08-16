"""add tmdb_id to show, season, and episode

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-18 02:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("show", sa.Column("tmdb_id", sa.Integer(), nullable=True))
    op.add_column("season", sa.Column("tmdb_id", sa.Integer(), nullable=True))
    op.add_column("episode", sa.Column("tmdb_id", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("episode", "tmdb_id")
    op.drop_column("season", "tmdb_id")
    op.drop_column("show", "tmdb_id")
