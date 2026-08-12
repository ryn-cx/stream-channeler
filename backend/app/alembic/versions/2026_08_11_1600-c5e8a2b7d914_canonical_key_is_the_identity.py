"""let the key be the whole of what a canonical row is

`tmdb_media_type` and `tmdb_id` said the same thing the key already said, in a
second place, so a row could be written where the two disagreed. They are
dropped and everything reads the key.

The keys are rewritten as they go, because the pair carried something the old
key did not: which level the id belongs to. TMDB files a film as a title, a
season and an episode all carrying the film's own number, so "TMDB movie 550"
named three different rows. "TMDB movie show 550", "TMDB movie season 550" and
"TMDB movie episode 550" name one each.

The half of the catalogue stays in the key. TMDB numbers films and series
separately, so an id means nothing without it.

Revision ID: c5e8a2b7d914
Revises: a3d9f61c47e8
Create Date: 2026-08-11 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c5e8a2b7d914"
down_revision = "a3d9f61c47e8"
branch_labels = None
depends_on = None

# Each canonical table, the level its rows are of, and the constraints that
# spanned the pair being dropped.
LEVELS = (
    (
        "canonicalshow",
        "show",
        "CanonicalShow-tmdb_media_type-tmdb_id-key",
        "CanonicalShow-tmdb-identity-complete",
    ),
    (
        "canonicalseason",
        "season",
        "CanonicalSeason-tmdb_media_type-tmdb_id-key",
        "CanonicalSeason-tmdb-identity-complete",
    ),
    (
        "canonicalepisode",
        "episode",
        "CanonicalEpisode-tmdb_media_type-tmdb_id-key",
        "CanonicalEpisode-tmdb-identity-complete",
    ),
)


def upgrade():
    # Before the column it is on goes, since Postgres takes the index with the
    # column and there would be nothing left to drop.
    op.drop_index("CanonicalShow-tmdb_id-index", table_name="canonicalshow")

    for table, level, unique, check in LEVELS:
        op.execute(
            f"""
            UPDATE {table}
            SET key = 'TMDB ' || tmdb_media_type || ' {level} ' || tmdb_id
            WHERE tmdb_id IS NOT NULL
            """,  # noqa: S608 - Table and level names come from the tuple above.
        )
        op.drop_constraint(check, table, type_="check")
        op.drop_constraint(unique, table, type_="unique")
        op.drop_column(table, "tmdb_id")
        op.drop_column(table, "tmdb_media_type")

    # An episode is looked up by key alone where a `User` names a TMDB id by
    # hand, which is across every season rather than within one.
    op.create_index("CanonicalEpisode-key-index", "canonicalepisode", ["key"])


def downgrade():
    op.drop_index("CanonicalEpisode-key-index", table_name="canonicalepisode")

    for table, level, unique, check in LEVELS:
        op.add_column(table, sa.Column("tmdb_media_type", sa.String(), nullable=True))
        op.add_column(table, sa.Column("tmdb_id", sa.Integer(), nullable=True))
        op.execute(
            f"""
            UPDATE {table}
            SET tmdb_media_type = split_part(key, ' ', 2),
                tmdb_id = split_part(key, ' ', 4)::integer
            WHERE key LIKE 'TMDB % {level} %'
            """,  # noqa: S608 - Table and level names come from the tuple above.
        )
        op.execute(
            f"""
            UPDATE {table}
            SET key = 'TMDB ' || tmdb_media_type || ' ' || tmdb_id
            WHERE tmdb_id IS NOT NULL
            """,  # noqa: S608 - Table names come from the tuple above.
        )
        op.create_unique_constraint(unique, table, ["tmdb_media_type", "tmdb_id"])
        op.create_check_constraint(
            check,
            table,
            "(tmdb_media_type IS NULL) = (tmdb_id IS NULL)",
        )

    op.create_index("CanonicalShow-tmdb_id-index", "canonicalshow", ["tmdb_id"])
