import sqlalchemy as sa
from alembic import op

revision = "a5c0e38fb629"
down_revision = "f4b9d27ea518"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "unmatchedsource",
        sa.Column("ignored_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("unmatchedsource", "ignored_at")
