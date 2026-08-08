"""let a combined channel be read with its own default filters

Revision ID: d51e6b3a2c47
Revises: c3f5a92d17be
Create Date: 2026-08-07 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d51e6b3a2c47"
down_revision = "c3f5a92d17be"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "channelcombinedchannel",
        sa.Column(
            "use_default_filters",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        "channelcombinedchannel",
        "use_default_filters",
        server_default=None,
    )


def downgrade():
    op.drop_column("channelcombinedchannel", "use_default_filters")
