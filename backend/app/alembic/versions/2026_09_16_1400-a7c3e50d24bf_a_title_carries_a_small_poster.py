import sqlalchemy as sa
from alembic import op

revision = "a7c3e50d24bf"
down_revision = "b83f5c1d97ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "title",
        sa.Column("poster_thumbnail_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("title", "poster_thumbnail_url")
