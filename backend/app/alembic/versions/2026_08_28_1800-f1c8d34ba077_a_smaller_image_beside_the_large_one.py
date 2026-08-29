import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "f1c8d34ba077"
down_revision = "c7e2a53bd841"
branch_labels = None
depends_on = None

TABLES = ("show", "season", "episode")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "thumbnail_url",
                sqlmodel.sql.sqltypes.AutoString(),
                nullable=True,
            ),
        )
        op.execute(f"UPDATE {table} SET thumbnail_url = image_url")  # noqa: S608


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "thumbnail_url")
