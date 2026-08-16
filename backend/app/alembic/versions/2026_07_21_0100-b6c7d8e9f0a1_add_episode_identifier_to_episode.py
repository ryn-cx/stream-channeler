"""add episode_identifier to episode

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-07-21 01:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b6c7d8e9f0a1"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "episode", sa.Column("episode_identifier", sa.String(), nullable=True)
    )


def downgrade():
    op.drop_column("episode", "episode_identifier")
