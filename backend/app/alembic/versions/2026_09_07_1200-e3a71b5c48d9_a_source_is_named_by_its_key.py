import sqlalchemy as sa
from alembic import op

revision = "e3a71b5c48d9"
down_revision = "c5d9028e4b17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE title
        SET source_id = old_source.id
        FROM plugin, source AS new_source, source AS old_source
        WHERE plugin.key = 'CustomMedia'
          AND new_source.plugin_id = plugin.id
          AND new_source.key = 'Custom Media'
          AND old_source.plugin_id = plugin.id
          AND old_source.key = 'CustomMedia'
          AND title.source_id = new_source.id
          AND NOT EXISTS (
              SELECT 1
              FROM title AS kept_title
              WHERE kept_title.source_id = old_source.id
                AND kept_title.key = title.key
          )
        """,
    )
    op.execute(
        """
        DELETE FROM source
        USING plugin, source AS old_source
        WHERE plugin.key = 'CustomMedia'
          AND source.plugin_id = plugin.id
          AND source.key = 'Custom Media'
          AND old_source.plugin_id = plugin.id
          AND old_source.key = 'CustomMedia'
        """,
    )
    op.execute(
        """
        DELETE FROM usersourcepreference AS old_preference
        USING usersourcepreference AS new_preference
        WHERE old_preference.source_key = 'CustomMedia'
          AND new_preference.source_key = 'Custom Media'
          AND new_preference.user_id = old_preference.user_id
        """,
    )
    op.execute(
        """
        UPDATE usersourcepreference
        SET source_key = 'Custom Media'
        WHERE source_key = 'CustomMedia'
        """,
    )
    op.execute(
        """
        UPDATE source
        SET key = 'Custom Media'
        FROM plugin
        WHERE plugin.id = source.plugin_id
          AND plugin.key = 'CustomMedia'
          AND source.key = 'CustomMedia'
        """,
    )
    op.drop_index("Source-name-index", table_name="source")
    op.create_index("Source-key-index", "source", ["key"])
    op.drop_column("source", "name")


def downgrade() -> None:
    op.add_column("source", sa.Column("name", sa.String(), nullable=True))
    op.execute("UPDATE source SET name = key")
    op.drop_index("Source-key-index", table_name="source")
    op.create_index("Source-name-index", "source", ["name"])
    op.execute(
        """
        UPDATE source
        SET key = 'CustomMedia', name = 'Custom Media'
        FROM plugin
        WHERE plugin.id = source.plugin_id
          AND plugin.key = 'CustomMedia'
          AND source.key = 'Custom Media'
        """,
    )
    op.execute(
        """
        UPDATE usersourcepreference
        SET source_key = 'CustomMedia'
        WHERE source_key = 'Custom Media'
        """,
    )
