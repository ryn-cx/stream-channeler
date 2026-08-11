"""give every canonical row one key that says what it is

TMDB could say two of its records were the same work, because it wrote a
`(tmdb_media_type, tmdb_id)` pair every copy naming that record resolved to.
Nothing else could say anything of the kind, so a YouTube video that appeared
under both a channel's uploads and one of its playlists became two canonical
episodes with nothing to draw them back together.

A `url` column comes with it: the page of the work itself, as against a copy's
own `url`, which is where one website streams it.

`key` is that pair generalised: one namespaced string any plugin can issue.
"TMDB tv 1234" is what the pair used to say; "YouTube dQw4w9WgXcQ" is what a
video only YouTube knows about says. Unique, so two copies claiming the same key
are one row by construction.

The TMDB columns stay. They are what a themoviedb.org link is built from and
what the matching runs over, and reading them back out of the key would put the
string parsing this whole split removed straight back in. They are written
beside the key rather than instead of it.

Revision ID: a3d9f61c47e8
Revises: f2a7c8e4b593
Create Date: 2026-08-11 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3d9f61c47e8"
down_revision = "f2a7c8e4b593"
branch_labels = None
depends_on = None

# Each canonical table, the constraint naming its key, and the columns that
# constraint spans. A key means one thing under the row holding it rather than
# across the whole table, since that is all a plugin promises of its own keys.
LEVELS = (
    ("canonicalshow", "CanonicalShow-key-key", ["key"]),
    (
        "canonicalseason",
        "CanonicalSeason-canonical_show_id-key-key",
        ["canonical_show_id", "key"],
    ),
    (
        "canonicalepisode",
        "CanonicalEpisode-canonical_season_id-key-key",
        ["canonical_season_id", "key"],
    ),
)


def upgrade():
    for table, constraint, columns in LEVELS:
        op.add_column(table, sa.Column("key", sa.String(), nullable=True))
        op.add_column(table, sa.Column("url", sa.String(), nullable=True))
        # A row TMDB holds already had an identity; it is spelled out here so
        # the key and the pair say the same thing from the start.
        op.execute(
            f"""
            UPDATE {table}
            SET key = 'TMDB ' || tmdb_media_type || ' ' || tmdb_id
            WHERE tmdb_id IS NOT NULL
            """,  # noqa: S608 - Table names come from the tuple above.
        )
        op.create_unique_constraint(constraint, table, columns)


def downgrade():
    for table, constraint, _columns in LEVELS:
        op.drop_constraint(constraint, table, type_="unique")
        op.drop_column(table, "url")
        op.drop_column(table, "key")
