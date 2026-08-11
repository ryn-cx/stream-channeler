"""give every canonical row one key that says what it is

TMDB could say two of its records were the same work, because it wrote a
`(tmdb_media_type, tmdb_id)` pair every copy naming that record resolved to.
Nothing else could say anything of the kind, so a YouTube video that appeared
under both a channel's uploads and one of its playlists became two canonical
episodes with nothing to draw them back together.

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

TABLES = ("canonicalshow", "canonicalseason", "canonicalepisode")
CONSTRAINTS = {
    "canonicalshow": "CanonicalShow-key-key",
    "canonicalseason": "CanonicalSeason-key-key",
    "canonicalepisode": "CanonicalEpisode-key-key",
}


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("key", sa.String(), nullable=True))
        # A row TMDB holds already had an identity; it is spelled out here so
        # the key and the pair say the same thing from the start.
        op.execute(
            f"""
            UPDATE {table}
            SET key = 'TMDB ' || tmdb_media_type || ' ' || tmdb_id
            WHERE tmdb_id IS NOT NULL
            """,  # noqa: S608 - Table names come from the tuple above.
        )
        op.create_unique_constraint(CONSTRAINTS[table], table, ["key"])


def downgrade():
    for table in TABLES:
        op.drop_constraint(CONSTRAINTS[table], table, type_="unique")
        op.drop_column(table, "key")
