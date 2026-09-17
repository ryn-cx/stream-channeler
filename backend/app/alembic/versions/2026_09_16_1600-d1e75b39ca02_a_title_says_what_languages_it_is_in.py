# TODO: Validate
"""A title says what languages it is in."""

import sqlalchemy as sa
from alembic import op

revision = "d1e75b39ca02"
down_revision = "c9f42a0b7e13"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.add_column("title", sa.Column("original_language", sa.String(), nullable=True))
    op.create_table(
        "titlespokenlanguage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["title_id"], ["title.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("title_id", "code"),
        sa.UniqueConstraint("id"),
    )
    op.create_index("TitleSpokenLanguage-code-index", "titlespokenlanguage", ["code"])


# TODO: Validate
def downgrade() -> None:
    op.drop_index("TitleSpokenLanguage-code-index", table_name="titlespokenlanguage")
    op.drop_table("titlespokenlanguage")
    op.drop_column("title", "original_language")
