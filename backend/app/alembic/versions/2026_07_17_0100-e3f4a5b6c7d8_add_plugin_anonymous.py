"""add plugin anonymous

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-17 01:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade():
    # server_default backfills the existing rows, then it is dropped so the model's
    # Python-side default is the only one, matching how `channel.anonymous` was added.
    op.add_column(
        "plugin",
        sa.Column("anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("plugin", "anonymous", server_default=None)


def downgrade():
    op.drop_column("plugin", "anonymous")
