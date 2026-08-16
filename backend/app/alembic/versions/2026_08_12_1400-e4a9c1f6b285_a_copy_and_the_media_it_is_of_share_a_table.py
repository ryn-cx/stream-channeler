"""a copy and the media it is of share a table

A website's listing and the media it is a listing of were two tables of the same
shape, and everything that read one had to know which of the two it was holding.
They are one table now, and a row says which it is by the pointer a copy carries
to the row it stands for: a row pointing at nothing is the media itself.

Nothing about the rows changes. Every id is kept, so the channel tables that name
a canonical row go on naming the same one and only the table they point at is
retargeted. The two hierarchies become one as well - a canonical season now hangs
off `show_id` like any other season, and a canonical episode off `season_id` -
which is why the copies' primary keys still hold: a parent id belongs either to a
canonical row or to a copy and never to both, so the two populations cannot
collide inside `(show_id, key)` or `(season_id, key)`.

A show pays for this where the other two levels do not. A canonical row has no
source, so `source_id` has to allow nothing, and a primary key cannot, so the
key moves to `id` and `(source_id, key)` becomes a partial unique index. The
canonical rows keep their own rule - one row per key across the whole table -
as a second partial index over the rows a copy pointer is absent from.

Two things are put right on the way past. The canonical tables never had the
four columns every media row carries - `data_timestamp`, `update_at`,
`deleted_at` and `extra` - so reading one through its model raised. They arrive
by the move itself, empty, which is what they say for a row no website supplied
and nothing can soft delete. And `icon` goes: it was copied onto these tables
when they were made, no model has ever named it, and no row has ever set it.

The pointers are left as `NO ACTION` rather than `RESTRICT`. Both refuse to
orphan a copy. `RESTRICT` is checked a row at a time and is not satisfied by the
referencing row being deleted in the same statement, which two tables could never
run into and one table would.

Revision ID: e4a9c1f6b285
Revises: d1b6f8c3e492
Create Date: 2026-08-12 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e4a9c1f6b285"
down_revision = "d1b6f8c3e492"
branch_labels = None
depends_on = None

# A parent id names either a canonical row or a copy, so the copies' primary keys
# hold across both populations. Counted rather than trusted, because the insert
# that follows would otherwise fail halfway through.
_COLLISION_CHECKS = """
DO $$
DECLARE
    clashes bigint;
BEGIN
    SELECT count(*) INTO clashes
    FROM canonicalseason
    JOIN season ON season.show_id = canonicalseason.canonical_show_id
               AND season.key = canonicalseason.key;
    IF clashes > 0 THEN
        RAISE EXCEPTION 'season (show_id, key) would collide on % rows', clashes;
    END IF;

    SELECT count(*) INTO clashes
    FROM canonicalepisode
    JOIN episode ON episode.season_id = canonicalepisode.canonical_season_id
                AND episode.key = canonicalepisode.key;
    IF clashes > 0 THEN
        RAISE EXCEPTION 'episode (season_id, key) would collide on % rows', clashes;
    END IF;

    SELECT count(*) INTO clashes FROM canonicalshow JOIN show ON show.id = canonicalshow.id;
    IF clashes > 0 THEN
        RAISE EXCEPTION 'show id would collide on % rows', clashes;
    END IF;
END $$;
"""

# The move itself. A canonical row arrives with no source and no pointer, which
# is the whole of what says it is the media rather than a listing of it.
_MOVE_SHOWS = """
INSERT INTO show (id, created_at, modified_at, key, name, media_type, description,
                  url, image_url, year, canonical_show_locked, canonical_show_id,
                  source_id)
SELECT id, created_at, modified_at, key, name, media_type, description,
       url, image_url, year, false, NULL, NULL
FROM canonicalshow
"""

_MOVE_SEASONS = """
INSERT INTO season (id, created_at, modified_at, key, name, url, season_number,
                    image_url, sort_order, show_id, canonical_season_id)
SELECT id, created_at, modified_at, key, name, url, season_number,
       image_url, sort_order, canonical_show_id, NULL
FROM canonicalseason
"""

_MOVE_EPISODES = """
INSERT INTO episode (id, created_at, modified_at, key, name, description, url,
                     image_url, air_date, episode_number, duration, sort_order,
                     season_id, canonical_episode_id, canonical_episode_locked)
SELECT id, created_at, modified_at, key, name, description, url,
       image_url, air_date, episode_number, duration, sort_order,
       canonical_season_id, NULL, false
FROM canonicalepisode
"""

# Every row is one of the two and nothing in between. A copy has both a source
# and a pointer; the media itself has neither.
_SHAPE_CHECK = """
DO $$
DECLARE
    wrong bigint;
BEGIN
    SELECT count(*) INTO wrong FROM show
    WHERE (source_id IS NULL) <> (canonical_show_id IS NULL);
    IF wrong > 0 THEN
        RAISE EXCEPTION '% show rows are neither a copy nor the media itself', wrong;
    END IF;

    SELECT count(*) INTO wrong FROM season s
    JOIN show ON show.id = s.show_id
    WHERE (s.canonical_season_id IS NULL) <> (show.canonical_show_id IS NULL);
    IF wrong > 0 THEN
        RAISE EXCEPTION '% season rows disagree with the show holding them', wrong;
    END IF;

    SELECT count(*) INTO wrong FROM episode e
    JOIN season ON season.id = e.season_id
    WHERE (e.canonical_episode_id IS NULL) <> (season.canonical_season_id IS NULL);
    IF wrong > 0 THEN
        RAISE EXCEPTION '% episode rows disagree with the season holding them', wrong;
    END IF;

    SELECT count(*) INTO wrong FROM channelshow c
    JOIN show ON show.id = c.canonical_show_id
    WHERE show.canonical_show_id IS NOT NULL;
    IF wrong > 0 THEN
        RAISE EXCEPTION '% channelshow rows name a copy rather than a title', wrong;
    END IF;

    SELECT count(*) INTO wrong FROM showcanonicalshow link
    JOIN show copy ON copy.id = link.show_id
    JOIN show title ON title.id = link.canonical_show_id
    WHERE copy.canonical_show_id IS NULL OR title.canonical_show_id IS NOT NULL;
    IF wrong > 0 THEN
        RAISE EXCEPTION '% showcanonicalshow rows link the wrong way round', wrong;
    END IF;
END $$;
"""

# Only the canonical rows are ordered by these, so only they are indexed for it.
_SORT_INDEXES = {
    "show": ("canonical_show_id", ["media_type", "name"]),
    "season": ("canonical_season_id", ["name", "season_number", "sort_order"]),
    "episode": (
        "canonical_episode_id",
        ["air_date", "duration", "episode_number", "name", "sort_order"],
    ),
}

_CANONICAL_TABLES = ("canonicalepisode", "canonicalseason", "canonicalshow")

# What already points at a show, all of it at `id`. The unique constraint they
# rest on has to go so that `id` can carry the primary key instead, and a foreign
# key cannot outlive what it rests on, so they are dropped and put back.
_SHOW_REFERENCES = (
    ("channelsourcefilter", "channelsourcefilter_show_id_fkey"),
    ("season", "season_show_id_fkey"),
    ("showcanonicalshow", "showcanonicalshow_show_id_fkey"),
    ("showissuereport", "showissuereport_show_id_fkey"),
)

# Each copy pointer, and the table it has to be retargeted from.
_SELF_POINTERS = (
    ("show", "canonical_show_id", "show_canonical_show_id_fkey"),
    ("season", "canonical_season_id", "season_canonical_season_id_fkey"),
    ("episode", "canonical_episode_id", "episode_canonical_episode_id_fkey"),
)

# What a channel holds, and the table each of them now names.
_CHANNEL_POINTERS = (
    ("channelshow", "canonical_show_id", "channelshow_canonical_show_id_fkey", "show"),
    (
        "channelseasonfilter",
        "canonical_season_id",
        "channelseasonfilter_canonical_season_id_fkey",
        "season",
    ),
    (
        "channelepisodefilter",
        "canonical_episode_id",
        "channelepisodefilter_canonical_episode_id_fkey",
        "episode",
    ),
    (
        "channelsavedepisodeorder",
        "canonical_episode_id",
        "channelsavedepisodeorder_canonical_episode_id_fkey",
        "episode",
    ),
)


def upgrade() -> None:
    op.execute(_COLLISION_CHECKS)

    op.drop_column("show", "icon")
    op.drop_column("canonicalshow", "icon")

    # `source_id` can no longer be half of a primary key, since a canonical row
    # has none, so the key moves to `id` and the rule it carried becomes an index
    # over the copies alone. It has to come first: a column cannot stop being
    # required while a primary key still holds it.
    for table, name in _SHOW_REFERENCES:
        op.drop_constraint(name, table, type_="foreignkey")
    op.execute("ALTER TABLE show DROP CONSTRAINT show_pkey")
    op.execute("ALTER TABLE show DROP CONSTRAINT show_id_key")
    op.execute("ALTER TABLE show ADD CONSTRAINT show_pkey PRIMARY KEY (id)")
    for table, name in _SHOW_REFERENCES:
        op.create_foreign_key(
            name,
            table,
            "show",
            ["show_id"],
            ["id"],
            ondelete="CASCADE",
        )
    op.execute(
        'CREATE UNIQUE INDEX "Show-source_id-key-key" ON show (source_id, key)'
        " WHERE source_id IS NOT NULL",
    )

    # A canonical row has no source and points at nothing, so both have to allow
    # nothing before one can be written.
    op.alter_column("show", "source_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("show", "canonical_show_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column(
        "season",
        "canonical_season_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.alter_column(
        "episode",
        "canonical_episode_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # Deepest last: a canonical season needs its title present, an episode its
    # season.
    op.execute(_MOVE_SHOWS)
    op.execute(_MOVE_SEASONS)
    op.execute(_MOVE_EPISODES)

    for table, column, name in _SELF_POINTERS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, table, [column], ["id"])

    op.drop_constraint(
        "showcanonicalshow_canonical_show_id_fkey",
        "showcanonicalshow",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "showcanonicalshow_canonical_show_id_fkey",
        "showcanonicalshow",
        "show",
        ["canonical_show_id"],
        ["id"],
        ondelete="CASCADE",
    )

    for table, column, name, target in _CHANNEL_POINTERS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name,
            table,
            target,
            [column],
            ["id"],
            ondelete="RESTRICT",
        )

    op.execute(
        'CREATE UNIQUE INDEX "Show-canonical-key-key" ON show (key)'
        " WHERE canonical_show_id IS NULL",
    )
    op.execute(
        'CREATE INDEX "Episode-canonical-key-index" ON episode (key)'
        " WHERE canonical_episode_id IS NULL",
    )
    for table, (pointer, fields) in _SORT_INDEXES.items():
        for field in fields:
            op.execute(
                f'CREATE INDEX "{table.capitalize()}-{field}-index"'
                f" ON {table} ({field}) WHERE {pointer} IS NULL",
            )

    # A copy names one episode at most within the season holding it, and the
    # canonical rows are no part of that rule.
    op.drop_index(
        "Episode-live-season_id-canonical_episode_id-key", table_name="episode"
    )
    op.execute(
        'CREATE UNIQUE INDEX "Episode-live-season_id-canonical_episode_id-key"'
        " ON episode (season_id, canonical_episode_id)"
        " WHERE deleted_at IS NULL AND canonical_episode_id IS NOT NULL",
    )

    for table in _CANONICAL_TABLES:
        op.drop_table(table)

    op.execute(_SHAPE_CHECK)


def downgrade() -> None:
    msg = (
        "The canonical tables cannot be rebuilt: the rows moved into the copy"
        " tables and nothing records which of them arrived that way beyond the"
        " pointer, which a later import may have changed."
    )
    raise NotImplementedError(msg)
