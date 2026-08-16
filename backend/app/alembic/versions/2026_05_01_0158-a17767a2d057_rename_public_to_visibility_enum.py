"""rename public to visibility enum

Revision ID: a17767a2d057
Revises: 3f3a4fef83b2
Create Date: 2026-05-01 01:58:12.707741

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "a17767a2d057"
down_revision = "3f3a4fef83b2"
branch_labels = None
depends_on = None


visibility_enum = sa.Enum("public", "unlisted", "private", name="visibility")


def _backfill(table: str, source_col: str) -> None:
    op.add_column(table, sa.Column("visibility", visibility_enum, nullable=True))
    op.execute(
        f"UPDATE {table} SET visibility = CASE WHEN {source_col} THEN 'public'::visibility ELSE 'private'::visibility END"
    )
    op.alter_column(table, "visibility", nullable=False)
    op.drop_column(table, source_col)


def _restore(table: str, target_col: str) -> None:
    op.add_column(table, sa.Column(target_col, sa.BOOLEAN(), nullable=True))
    op.execute(f"UPDATE {table} SET {target_col} = (visibility = 'public')")
    op.alter_column(table, target_col, nullable=False)
    op.drop_column(table, "visibility")


def upgrade():
    visibility_enum.create(op.get_bind(), checkfirst=True)
    _backfill("channel", "is_public")
    _backfill("playlist", "public")
    _backfill("plugin", "public")


def downgrade():
    _restore("plugin", "public")
    _restore("playlist", "public")
    _restore("channel", "is_public")
    visibility_enum.drop(op.get_bind(), checkfirst=True)
