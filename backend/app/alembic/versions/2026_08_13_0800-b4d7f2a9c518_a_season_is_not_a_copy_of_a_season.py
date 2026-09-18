"""a season is not a copy of a season

Revision ID: b4d7f2a9c518
Revises: f5b8d2a7c391
Create Date: 2026-08-13 08:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b4d7f2a9c518"
down_revision = "f5b8d2a7c391"
branch_labels = None
depends_on = None

_SORT_INDEXES = ("name", "season_number", "sort_order")


def upgrade() -> None:
    op.drop_constraint("season_canonical_season_id_fkey", "season", type_="foreignkey")
    op.drop_index("Season-canonical_season_id-index", table_name="season")
    for field in _SORT_INDEXES:
        op.drop_index(f"Season-{field}-index", table_name="season")
    op.drop_column("season", "canonical_season_id")
    for field in _SORT_INDEXES:
        op.create_index(f"Season-{field}-index", "season", [field])

    op.alter_column(
        "channelseasonfilter",
        "canonical_season_id",
        new_column_name="season_id",
    )
    op.execute(
        "ALTER TABLE channelseasonfilter RENAME CONSTRAINT"
        " channelseasonfilter_canonical_season_id_fkey TO"
        " channelseasonfilter_season_id_fkey",
    )
    op.execute(
        'ALTER INDEX "ChannelSeasonFilter-canonical_season_id-index"'
        ' RENAME TO "ChannelSeasonFilter-season_id-index"',
    )


def downgrade() -> None:
    op.execute(
        'ALTER INDEX "ChannelSeasonFilter-season_id-index"'
        ' RENAME TO "ChannelSeasonFilter-canonical_season_id-index"',
    )
    op.execute(
        "ALTER TABLE channelseasonfilter RENAME CONSTRAINT"
        " channelseasonfilter_season_id_fkey TO"
        " channelseasonfilter_canonical_season_id_fkey",
    )
    op.alter_column(
        "channelseasonfilter",
        "season_id",
        new_column_name="canonical_season_id",
    )

    for field in _SORT_INDEXES:
        op.drop_index(f"Season-{field}-index", table_name="season")
    op.add_column("season", sa.Column("canonical_season_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "season_canonical_season_id_fkey",
        "season",
        "season",
        ["canonical_season_id"],
        ["id"],
    )
    op.create_index(
        "Season-canonical_season_id-index", "season", ["canonical_season_id"]
    )
    for field in _SORT_INDEXES:
        op.execute(
            f'CREATE INDEX "Season-{field}-index" ON season ({field})'
            " WHERE canonical_season_id IS NULL",
        )
