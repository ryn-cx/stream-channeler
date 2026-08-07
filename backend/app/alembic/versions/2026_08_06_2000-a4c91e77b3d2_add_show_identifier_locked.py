"""add show_identifier_locked to show

Revision ID: a4c91e77b3d2
Revises: f1b7d24c8e93
Create Date: 2026-08-06 20:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a4c91e77b3d2"
down_revision = "f1b7d24c8e93"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "show",
        sa.Column(
            "show_identifier_locked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Every stored show was linked by a name search, so none of them are settled.
    op.alter_column("show", "show_identifier_locked", server_default=None)


def downgrade():
    op.drop_column("show", "show_identifier_locked")
