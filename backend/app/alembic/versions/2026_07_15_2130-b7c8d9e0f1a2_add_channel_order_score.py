"""add channel order score

Revision ID: b7c8d9e0f1a2
Revises: d9af2e3b8dcf
Create Date: 2026-07-15 21:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c8d9e0f1a2"
down_revision = "d9af2e3b8dcf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "channelorder",
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("channelorder", "score", server_default=None)


def downgrade():
    op.drop_column("channelorder", "score")
