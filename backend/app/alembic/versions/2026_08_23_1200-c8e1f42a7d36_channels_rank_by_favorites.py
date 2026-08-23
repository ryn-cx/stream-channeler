"""channels rank by favorites

Revision ID: c8e1f42a7d36
Revises: a3d7c081be24
Create Date: 2026-08-23 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c8e1f42a7d36"
down_revision = "a3d7c081be24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("channel", "score")


def downgrade() -> None:
    op.add_column(
        "channel",
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("channel", "score", server_default=None)
