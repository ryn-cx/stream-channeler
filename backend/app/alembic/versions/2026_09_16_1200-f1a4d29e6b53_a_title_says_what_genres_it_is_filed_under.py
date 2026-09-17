import sqlalchemy as sa
from alembic import op

revision = "f1a4d29e6b53"
down_revision = "d6b81c07f4a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "titlegenre",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["title_id"], ["title.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("title_id", "name"),
        sa.UniqueConstraint("id"),
    )
    op.create_index("TitleGenre-name-index", "titlegenre", ["name"])


def downgrade() -> None:
    op.drop_index("TitleGenre-name-index", table_name="titlegenre")
    op.drop_table("titlegenre")
