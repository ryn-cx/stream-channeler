"""index each media identifier for the live rows on their own

Revision ID: f73a5d9e28c1
Revises: e62f4c8d31ab
Create Date: 2026-08-09 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f73a5d9e28c1"
down_revision = "e62f4c8d31ab"
branch_labels = None
depends_on = None

# Every lookup by identifier wants the live record, and `deleted_at` holds
# nothing for nearly every row, so answering both halves out of the two plain
# indexes means reading every live row of the table for each lookup. The TMDB
# fallback join in the episode read does exactly that lookup once per candidate
# episode, which is what made it the slowest part of reading a channel.
_TABLES = {
    "episode": "episode_identifier",
    "season": "season_identifier",
    "show": "show_identifier",
}


def _index_name(table: str, column: str) -> str:
    return f"{table.capitalize()}-live-{column}-index"


def upgrade():
    for table, column in _TABLES.items():
        op.create_index(
            _index_name(table, column),
            table,
            [column],
            postgresql_where=sa.text("deleted_at IS NULL"),
        )


def downgrade():
    for table, column in _TABLES.items():
        op.drop_index(_index_name(table, column), table_name=table)
