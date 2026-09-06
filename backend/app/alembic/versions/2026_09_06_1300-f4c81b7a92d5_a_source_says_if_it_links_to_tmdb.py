import sqlalchemy as sa
from alembic import op

revision = "f4c81b7a92d5"
down_revision = "a1f7c93d20b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "source",
        sa.Column(
            "link_to_tmdb",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("source", "link_to_tmdb", server_default=None)
    op.execute(
        """
        UPDATE source
        SET link_to_tmdb = false
        FROM plugin
        WHERE plugin.id = source.plugin_id
          AND (
            plugin.key IN ('TMDB', 'YouTube')
            OR (plugin.key = 'Crunchyroll' AND source.key = 'Crunchyroll Music')
          )
        """,
    )


def downgrade() -> None:
    op.drop_column("source", "link_to_tmdb")
