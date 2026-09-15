import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "a1e7c53d9f24"
down_revision = "d2f9e45cb188"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("Plugin-name-index", table_name="plugin")
    op.drop_column("plugin", "name")


def downgrade() -> None:
    op.add_column(
        "plugin",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.execute("UPDATE plugin SET name = key")
    op.create_index("Plugin-name-index", "plugin", ["name"], unique=False)
