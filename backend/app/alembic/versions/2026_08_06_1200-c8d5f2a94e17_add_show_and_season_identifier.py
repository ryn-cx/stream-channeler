"""add show_identifier and season_identifier

Revision ID: c8d5f2a94e17
Revises: a1c4e7b93d52
Create Date: 2026-08-06 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "c8d5f2a94e17"
down_revision = "a1c4e7b93d52"
branch_labels = None
depends_on = None


def upgrade():
    # An episode already carried the identifier that makes the same episode on two
    # websites one episode. Shows and seasons get the same thing, so the copies of a
    # title spread across sources can be matched up as well.
    op.add_column(
        "show",
        sa.Column("show_identifier", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "season",
        sa.Column(
            "season_identifier", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )

    # TMDB is what ties copies together, so a linked record is identified by its TMDB
    # id. An unlinked one is only ever itself, so it falls back to the plugin's own key
    # for it, which is what the plugins write for new records.
    op.execute(
        """
        UPDATE show
        SET show_identifier = CASE
            WHEN show.tmdb_id IS NOT NULL THEN 'TMDB ' || show.tmdb_id
            ELSE plugin.key || ' ' || show.key
        END
        FROM source, plugin
        WHERE source.id = show.source_id
          AND plugin.id = source.plugin_id
        """
    )
    op.execute(
        """
        UPDATE season
        SET season_identifier = CASE
            WHEN season.tmdb_id IS NOT NULL THEN 'TMDB ' || season.tmdb_id
            ELSE plugin.key || ' ' || season.key
        END
        FROM show, source, plugin
        WHERE show.id = season.show_id
          AND source.id = show.source_id
          AND plugin.id = source.plugin_id
        """
    )

    op.alter_column(
        "show",
        "show_identifier",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )
    op.alter_column(
        "season",
        "season_identifier",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )

    op.create_index(
        "Show-show_identifier-index", "show", ["show_identifier", "id"], unique=False
    )
    op.create_index(
        "Season-season_identifier-index",
        "season",
        ["season_identifier", "id"],
        unique=False,
    )


def downgrade():
    op.drop_index("Season-season_identifier-index", table_name="season")
    op.drop_index("Show-show_identifier-index", table_name="show")
    op.drop_column("season", "season_identifier")
    op.drop_column("show", "show_identifier")
