import sqlalchemy as sa
from alembic import op

revision = "c5d9028e4b17"
down_revision = "b8e2d47f1a93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "title",
        sa.Column(
            "link_status",
            sa.String(),
            nullable=True,
            server_default="Linked",
        ),
    )
    op.alter_column("title", "link_status", server_default=None)
    op.create_index(
        "Title-link_status-index",
        "title",
        ["link_status"],
        postgresql_where=sa.text("link_status IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("Title-link_status-index", table_name="title")
    op.drop_column("title", "link_status")
