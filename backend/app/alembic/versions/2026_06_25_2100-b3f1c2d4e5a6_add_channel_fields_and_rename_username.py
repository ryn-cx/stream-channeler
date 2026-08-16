"""Add channel description/anonymous/score and rename user full_name to username

Revision ID: b3f1c2d4e5a6
Revises: 1ca97bd82157
Create Date: 2026-06-25 21:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "b3f1c2d4e5a6"
down_revision = "1ca97bd82157"
branch_labels = None
depends_on = None


def upgrade():
    # Channel: new owner-editable description/anonymous and admin-only score.
    op.add_column(
        "channel",
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "channel",
        sa.Column("anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("channel", "anonymous", server_default=None)
    op.add_column(
        "channel", sa.Column("score", sa.Integer(), nullable=False, server_default="0")
    )
    op.alter_column("channel", "score", server_default=None)

    # User: rename full_name -> username (an optional, non-unique display name).
    op.alter_column("user", "full_name", new_column_name="username")


def downgrade():
    op.alter_column("user", "username", new_column_name="full_name")
    op.drop_column("channel", "score")
    op.drop_column("channel", "anonymous")
    op.drop_column("channel", "description")
