"""merge tmdb_id into the identifier columns

Revision ID: b7d4e18c05fa
Revises: a4c91e77b3d2
Create Date: 2026-08-06 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7d4e18c05fa"
down_revision = "a4c91e77b3d2"
branch_labels = None
depends_on = None

# The identifier already carries the TMDB id of every linked record, so the
# column holding it a second time is dropped rather than migrated.
_TABLES = ("show", "season", "episode")


def upgrade():
    for table in _TABLES:
        op.drop_column(table, "tmdb_id")


def downgrade():
    for table in _TABLES:
        op.add_column(table, sa.Column("tmdb_id", sa.Integer(), nullable=True))

    # Read the id back out of `TMDB <media type> <id>`, which is where it lives now.
    for table, identifier in (
        ("show", "show_identifier"),
        ("season", "season_identifier"),
        ("episode", "episode_identifier"),
    ):
        op.execute(
            sa.text(
                f"""
                UPDATE {table}
                SET tmdb_id = CAST(split_part({identifier}, ' ', 3) AS INTEGER)
                WHERE {identifier} LIKE 'TMDB %'
                  AND split_part({identifier}, ' ', 3) ~ '^[0-9]+$'
                """,  # noqa: S608 - Table and column names are from the tuple above.
            ),
        )
