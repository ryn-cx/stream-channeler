import sqlalchemy as sa
from alembic import op

revision = "b6d1f49ac730"
down_revision = "a5c0e38fb629"
branch_labels = None
depends_on = None


visibility_enum = sa.Enum("public", "unlisted", "private", name="visibility")


def upgrade() -> None:
    # A key was only unique per owner, so the same key can be held by more than one
    # row. The oldest is kept and the rest are deleted along with their media.
    op.execute(
        """
        DELETE FROM plugin
        WHERE id NOT IN (
            SELECT DISTINCT ON (key) id FROM plugin ORDER BY key, created_at, id
        )
        """,
    )
    op.drop_index("Plugin-visibility-index", table_name="plugin")
    op.drop_constraint("plugin_user_id_fkey", "plugin", type_="foreignkey")
    op.drop_column("plugin", "user_id")
    op.drop_column("plugin", "visibility")
    op.drop_column("plugin", "anonymous")
    op.drop_constraint("file_plugin_id_fkey", "file", type_="foreignkey")
    op.drop_constraint("source_plugin_id_fkey", "source", type_="foreignkey")
    op.drop_constraint("plugin_pkey", "plugin", type_="primary")
    op.create_primary_key("plugin_pkey", "plugin", ["key"])
    op.create_foreign_key(
        "file_plugin_id_fkey",
        "file",
        "plugin",
        ["plugin_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "source_plugin_id_fkey",
        "source",
        "plugin",
        ["plugin_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("file_plugin_id_fkey", "file", type_="foreignkey")
    op.drop_constraint("source_plugin_id_fkey", "source", type_="foreignkey")
    op.drop_constraint("plugin_pkey", "plugin", type_="primary")
    op.create_primary_key("plugin_pkey", "plugin", ["id"])
    op.create_foreign_key(
        "file_plugin_id_fkey",
        "file",
        "plugin",
        ["plugin_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "source_plugin_id_fkey",
        "source",
        "plugin",
        ["plugin_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column("plugin", sa.Column("anonymous", sa.Boolean(), nullable=True))
    op.add_column("plugin", sa.Column("visibility", visibility_enum, nullable=True))
    op.add_column("plugin", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE plugin
        SET anonymous = false,
            visibility = 'unlisted'::visibility,
            user_id = COALESCE(
                (SELECT id FROM "user" WHERE email = 'plugins@streamchanneler.com'),
                (SELECT id FROM "user" ORDER BY created_at LIMIT 1)
            )
        """,
    )
    op.alter_column("plugin", "anonymous", nullable=False)
    op.alter_column("plugin", "visibility", nullable=False)
    op.alter_column("plugin", "user_id", nullable=False)
    op.create_foreign_key(
        "plugin_user_id_fkey",
        "plugin",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("Plugin-visibility-index", "plugin", ["visibility"])
