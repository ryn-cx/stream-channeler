"""Add snapshot anonymous and score

Revision ID: a1b2c3d4e5f6
Revises: f0e1d2c3b4a5
Create Date: 2026-07-01 01:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f0e1d2c3b4a5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "snapshot",
        sa.Column("anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("snapshot", "anonymous", server_default=None)
    op.add_column(
        "snapshot", sa.Column("score", sa.Integer(), nullable=False, server_default="0")
    )
    op.alter_column("snapshot", "score", server_default=None)


def downgrade():
    op.drop_column("snapshot", "score")
    op.drop_column("snapshot", "anonymous")
