"""an unmatched source is an unmatched title

The row says that TMDB lists a service carrying a title and that nothing here
carries it, which is a fact about the title rather than about a source: there is
no `Source` row for it, and there will not be one until somebody hands the import
a URL. The table is named for what it holds.

Revision ID: d6b81c07f4a2
Revises: c4a9e1b73f28
Create Date: 2026-09-12 13:00:00.000000

"""

from alembic import op

revision = "d6b81c07f4a2"
down_revision = "c4a9e1b73f28"
branch_labels = None
depends_on = None

TABLE = ("unmatchedsource", "unmatchedtitle")

INDEXES = [("UnmatchedSource-title_id-index", "UnmatchedTitle-title_id-index")]

CONSTRAINTS = [
    (
        "UnmatchedSource-title_id-provider_name-unique",
        "UnmatchedTitle-title_id-provider_name-unique",
    ),
]


def upgrade() -> None:
    old_table, new_table = TABLE
    op.rename_table(old_table, new_table)
    for old_name, new_name in INDEXES:
        op.execute(f'ALTER INDEX "{old_name}" RENAME TO "{new_name}"')
    for old_name, new_name in CONSTRAINTS:
        op.execute(
            f'ALTER TABLE {new_table} RENAME CONSTRAINT "{old_name}" TO "{new_name}"',
        )


def downgrade() -> None:
    old_table, new_table = TABLE
    for old_name, new_name in CONSTRAINTS:
        op.execute(
            f'ALTER TABLE {new_table} RENAME CONSTRAINT "{new_name}" TO "{old_name}"',
        )
    for old_name, new_name in INDEXES:
        op.execute(f'ALTER INDEX "{new_name}" RENAME TO "{old_name}"')
    op.rename_table(new_table, old_table)
