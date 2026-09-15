# TODO: Validate
"""An episode carries a note about what it stands for on TMDB."""

import sqlalchemy as sa
from alembic import op

revision = "e5b27a91c4d8"
down_revision = "c8d40f7b21e6"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.add_column("episode", sa.Column("tmdb_note", sa.String(), nullable=True))


# TODO: Validate
def downgrade() -> None:
    op.drop_column("episode", "tmdb_note")
