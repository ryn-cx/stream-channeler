"""no title a listing mixes comes first

A listing carried one of its titles in a column of its own, which made that title
the one the listing was chiefly of: the one its name and metadata were filled in
from, the one a caller with room for one was handed. A website that files two
titles under one listing is as much each of them as the other, so there is nothing
for that column to say and it goes.

Which titles a listing is of was already stored in `showcanonicalshow`, and the
column's title was written there alongside the rest, so nothing is lost by
dropping it. Any listing whose column named a title that never reached the table
has that link written in first.

Telling a listing from a title was the column's other job. That becomes
`is_canonical`, which says only which of the two a row is and nothing about what a
listing stands for.

Revision ID: c7e1a4b8d635
Revises: b4d7f2a9c518
Create Date: 2026-08-13 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7e1a4b8d635"
down_revision = "b4d7f2a9c518"
branch_labels = None
depends_on = None

_SORT_INDEXES = ("media_type", "name")

# A listing's own title has a row here already in every ordinary case; this is
# for the rows written since, where only the column was set.
_BACKFILL_LINKS = """
    INSERT INTO showcanonicalshow (id, created_at, modified_at, show_id,
                                   canonical_show_id)
    SELECT gen_random_uuid(), now(), now(), show.id, show.canonical_show_id
    FROM show
    WHERE show.canonical_show_id IS NOT NULL
    ON CONFLICT (show_id, canonical_show_id) DO NOTHING
"""

# A row that was a copy of something is a listing, and so is a row that is linked
# to a title without ever having carried one in the column.
_BACKFILL_FLAG = """
    UPDATE show
    SET is_canonical = FALSE
    WHERE canonical_show_id IS NOT NULL
       OR EXISTS (
           SELECT 1 FROM showcanonicalshow
           WHERE showcanonicalshow.show_id = show.id
       )
"""

# The one rule the flag has to keep: a row other rows are copies of is a title
# and is a copy of nothing itself.
_DEPTH_CHECK = """
    DO $$
    DECLARE offending int;
    BEGIN
        SELECT count(*) INTO offending
        FROM show
        WHERE NOT show.is_canonical
          AND EXISTS (
              SELECT 1 FROM showcanonicalshow
              WHERE showcanonicalshow.canonical_show_id = show.id
          );
        IF offending > 0 THEN
            RAISE EXCEPTION
                '% shows stand for a title and are stood for by one', offending;
        END IF;
    END $$
"""


def upgrade() -> None:
    op.add_column(
        "show",
        sa.Column(
            "is_canonical",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute(_BACKFILL_LINKS)
    op.execute(_BACKFILL_FLAG)
    op.execute(_DEPTH_CHECK)
    op.alter_column("show", "is_canonical", server_default=None)

    # Every index narrowed to the rows that pointed at nothing is narrowed to the
    # rows the flag calls titles instead, which is the same set of rows.
    op.drop_index("Show-canonical-key-key", table_name="show")
    for field in _SORT_INDEXES:
        op.drop_index(f"Show-{field}-index", table_name="show")
    op.execute('DROP INDEX IF EXISTS "Show-canonical_show_id-index"')
    op.drop_constraint("show_canonical_show_id_fkey", "show", type_="foreignkey")
    op.drop_column("show", "canonical_show_id")

    op.execute(
        'CREATE UNIQUE INDEX "Show-canonical-key-key" ON show (key)'
        " WHERE is_canonical IS TRUE",
    )
    for field in _SORT_INDEXES:
        op.execute(
            f'CREATE INDEX "Show-{field}-index" ON show ({field})'
            " WHERE is_canonical IS TRUE",
        )
    op.create_index("Show-is_canonical-index", "show", ["is_canonical"])


def downgrade() -> None:
    op.drop_index("Show-is_canonical-index", table_name="show")
    for field in _SORT_INDEXES:
        op.drop_index(f"Show-{field}-index", table_name="show")
    op.drop_index("Show-canonical-key-key", table_name="show")

    op.add_column("show", sa.Column("canonical_show_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "show_canonical_show_id_fkey",
        "show",
        "show",
        ["canonical_show_id"],
        ["id"],
    )
    # Which title a listing was chiefly of is not recorded anywhere, so the
    # earliest link it carries stands in for it. A listing of one title comes
    # back exactly as it was; one that mixes titles comes back naming whichever
    # of them was linked first.
    op.execute(
        """
        UPDATE show
        SET canonical_show_id = (
            SELECT showcanonicalshow.canonical_show_id
            FROM showcanonicalshow
            WHERE showcanonicalshow.show_id = show.id
            ORDER BY showcanonicalshow.created_at, showcanonicalshow.id
            LIMIT 1
        )
        WHERE NOT show.is_canonical
        """,
    )
    op.drop_column("show", "is_canonical")

    op.create_index("Show-canonical_show_id-index", "show", ["canonical_show_id"])
    op.execute(
        'CREATE UNIQUE INDEX "Show-canonical-key-key" ON show (key)'
        " WHERE canonical_show_id IS NULL",
    )
    for field in _SORT_INDEXES:
        op.execute(
            f'CREATE INDEX "Show-{field}-index" ON show ({field})'
            " WHERE canonical_show_id IS NULL",
        )
