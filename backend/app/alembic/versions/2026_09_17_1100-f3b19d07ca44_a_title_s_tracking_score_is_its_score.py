# TODO: Validate
"""A title's tracking score is its score."""

from alembic import op

revision = "f3b19d07ca44"
down_revision = "e2a86c41f7b9"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.alter_column("title", "tracking_score", new_column_name="score")


# TODO: Validate
def downgrade() -> None:
    op.alter_column("title", "score", new_column_name="tracking_score")
