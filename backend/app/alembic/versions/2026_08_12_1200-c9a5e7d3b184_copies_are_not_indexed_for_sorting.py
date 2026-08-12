"""a copy's own columns are not indexed for sorting

The columns a channel sorts on are read off the canonical row alone, so an index
on a copy's `name`, number, date or duration was never reachable from a channel.
The one thing that does order by them is the admin tables, and those order by any
column they show - a url, a key, a timestamp - which these five never covered, so
they earned their keep nowhere while still being maintained on every import.

The canonical tables keep theirs, which is where the sorting happens.

Revision ID: c9a5e7d3b184
Revises: b8f4d3e6c729
Create Date: 2026-08-12 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c9a5e7d3b184"
down_revision = "b8f4d3e6c729"
branch_labels = None
depends_on = None

_INDEXES = (
    ("Episode-air_date-index", "episode", "air_date"),
    ("Episode-duration-index", "episode", "duration"),
    ("Episode-episode_number-index", "episode", "episode_number"),
    ("Episode-name-index", "episode", "name"),
    ("Episode-sort_order-index", "episode", "sort_order"),
    ("Season-name-index", "season", "name"),
    ("Season-season_number-index", "season", "season_number"),
    ("Season-sort_order-index", "season", "sort_order"),
    ("Show-media_type-index", "show", "media_type"),
    ("Show-name-index", "show", "name"),
)


def upgrade():
    for name, table, _column in _INDEXES:
        op.drop_index(name, table_name=table)


def downgrade():
    for name, table, column in _INDEXES:
        op.create_index(name, table, [column])
