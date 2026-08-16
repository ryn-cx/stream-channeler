"""add channel favorite customization

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-18 01:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("channelfavorite", sa.Column("name", sa.String(), nullable=True))
    op.add_column(
        "channelfavorite", sa.Column("channel_number", sa.Float(), nullable=True)
    )


def downgrade():
    op.drop_column("channelfavorite", "channel_number")
    op.drop_column("channelfavorite", "name")
