"""drop the combined channel's own filters

Revision ID: b8e1c7a204df
Revises: f73a5d9e28c1
Create Date: 2026-08-09 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8e1c7a204df"
down_revision = "f73a5d9e28c1"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("channelcombinedchannel", "use_default_filters")


def downgrade():
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
