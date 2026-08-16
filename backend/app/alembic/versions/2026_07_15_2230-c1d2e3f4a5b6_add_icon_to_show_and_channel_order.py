"""add icon to show and channel order

Revision ID: c1d2e3f4a5b6
Revises: b7c8d9e0f1a2
Create Date: 2026-07-15 22:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "show",
        sa.Column("icon", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
    )
    op.add_column(
        "channelorder",
        sa.Column("icon", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
    )


def downgrade():
    op.drop_column("channelorder", "icon")
    op.drop_column("show", "icon")
