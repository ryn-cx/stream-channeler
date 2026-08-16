"""Add server_side_threshold to user

Revision ID: c4d5e6f7a8b9
Revises: b3f1c2d4e5a6
Create Date: 2026-06-27 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3f1c2d4e5a6"
branch_labels = None
depends_on = None


def upgrade():
    # Per-user row count at/above which media tables are filtered server-side.
    op.add_column(
        "user",
        sa.Column(
            "server_side_threshold",
            sa.Integer(),
            nullable=False,
            server_default="10000",
        ),
    )
    op.alter_column("user", "server_side_threshold", server_default=None)


def downgrade():
    op.drop_column("user", "server_side_threshold")
