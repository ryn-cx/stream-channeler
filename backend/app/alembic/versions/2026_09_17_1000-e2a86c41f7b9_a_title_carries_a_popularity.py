# TODO: Validate
"""A title carries a popularity."""

import sqlalchemy as sa
from alembic import op

revision = "e2a86c41f7b9"
down_revision = "d1e75b39ca02"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.add_column("title", sa.Column("popularity", sa.Float(), nullable=True))


# TODO: Validate
def downgrade() -> None:
    op.drop_column("title", "popularity")
