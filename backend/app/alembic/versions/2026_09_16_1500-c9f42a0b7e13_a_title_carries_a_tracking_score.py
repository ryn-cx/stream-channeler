# TODO: Validate
"""A title carries a tracking score."""

import sqlalchemy as sa
from alembic import op

revision = "c9f42a0b7e13"
down_revision = "a7c3e50d24bf"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.add_column("title", sa.Column("tracking_score", sa.Float(), nullable=True))


# TODO: Validate
def downgrade() -> None:
    op.drop_column("title", "tracking_score")
