import sqlalchemy as sa
from alembic import op

revision = "e3a8c46b19f5"
down_revision = "d9f2a51c83e7"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("show", "canonical_show_locked", "canonical_show_validated_at"),
    ("episode", "canonical_episode_locked", "canonical_episode_validated_at"),
)


_PRE_VALIDATED = (
    "plugin.key = 'TMDB'",
    "plugin.key = 'YouTube' AND show.media_type = 'YouTube Channel'",
    "plugin.key = 'Crunchyroll' AND source.key = 'Crunchyroll Music'",
)


def upgrade() -> None:
    for table, boolean_column, timestamp_column in _COLUMNS:
        op.add_column(
            table,
            sa.Column(timestamp_column, sa.DateTime(timezone=True), nullable=True),
        )
        op.execute(
            f"UPDATE {table} SET {timestamp_column} = now() WHERE {boolean_column}",
        )
        op.drop_column(table, boolean_column)

    for condition in _PRE_VALIDATED:
        op.execute(
            f"""
            UPDATE show
            SET canonical_show_validated_at = now()
            FROM source, plugin
            WHERE source.id = show.source_id
              AND plugin.id = source.plugin_id
              AND show.canonical_show_validated_at IS NULL
              AND {condition}
            """,
        )


def downgrade() -> None:
    for table, boolean_column, timestamp_column in _COLUMNS:
        op.add_column(
            table,
            sa.Column(
                boolean_column,
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
        op.execute(
            f"UPDATE {table} SET {boolean_column} = true"
            f" WHERE {timestamp_column} IS NOT NULL",
        )
        op.alter_column(table, boolean_column, server_default=None)
        op.drop_column(table, timestamp_column)
