"""every canonical row is named by its key

A row nothing could name was a row nothing could converge on: the flush hook
minted one for every copy it saw, and only `reconcile_show` running to the end
moved the copy off it and swept it up. Whatever it missed stayed as a title,
season or episode that no key reaches and no import can find again.

The key a copy spells out - the plugin that issued it and the copy's own key -
is now written when the row is made, so there is nothing nameless to sweep up.
Rows already stored are given that same key, read back off whichever copy points
at them; ones no copy points at are dropped, and two rows a key now names as one
are merged onto the older of them.

Revision ID: e7b3d1a9c206
Revises: d2f8a71c04b3
Create Date: 2026-08-12 08:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e7b3d1a9c206"
down_revision = "d2f8a71c04b3"
branch_labels = None
depends_on = None

# The key a copy spells out, which is what the flush hook now writes.
_SHOW_KEY = """
    UPDATE canonicalshow AS canonical
    SET key = plugin.key || ' ' || show.key
    FROM show
    JOIN source ON source.id = show.source_id
    JOIN plugin ON plugin.id = source.plugin_id
    WHERE canonical.key IS NULL AND show.canonical_show_id = canonical.id
"""

_SEASON_KEY = """
    UPDATE canonicalseason AS canonical
    SET key = plugin.key || ' ' || season.key
    FROM season
    JOIN show ON show.id = season.show_id
    JOIN source ON source.id = show.source_id
    JOIN plugin ON plugin.id = source.plugin_id
    WHERE canonical.key IS NULL AND season.canonical_season_id = canonical.id
"""

_EPISODE_KEY = """
    UPDATE canonicalepisode AS canonical
    SET key = plugin.key || ' ' || episode.key
    FROM episode
    JOIN season ON season.id = episode.season_id
    JOIN show ON show.id = season.show_id
    JOIN source ON source.id = show.source_id
    JOIN plugin ON plugin.id = source.plugin_id
    WHERE canonical.key IS NULL AND episode.canonical_episode_id = canonical.id
"""

# Two rows one key now names are one row. The oldest is kept, since it is the
# one anything else already stored is most likely to be pointing at.
_SHOW_DUPLICATES = """
    CREATE TEMPORARY TABLE merged_shows AS
    SELECT id AS dropped, first_value(id) OVER (
        PARTITION BY key ORDER BY created_at, id
    ) AS kept
    FROM canonicalshow
"""

_SEASON_DUPLICATES = """
    CREATE TEMPORARY TABLE merged_seasons AS
    SELECT id AS dropped, first_value(id) OVER (
        PARTITION BY canonical_show_id, key ORDER BY created_at, id
    ) AS kept
    FROM canonicalseason
"""

_EPISODE_DUPLICATES = """
    CREATE TEMPORARY TABLE merged_episodes AS
    SELECT id AS dropped, first_value(id) OVER (
        PARTITION BY canonical_season_id, key ORDER BY created_at, id
    ) AS kept
    FROM canonicalepisode
"""


# Dropped while the keys are written, since a key being filled in is exactly
# where two rows turn out to be one, and they are merged a few statements later.
_UNIQUE_KEYS = (
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
    for table, constraint, _columns in _UNIQUE_KEYS:
        op.drop_constraint(constraint, table, type_="unique")

    op.execute(_SHOW_KEY)
    op.execute(_SEASON_KEY)
    op.execute(_EPISODE_KEY)

    # A row no copy points at is one the backfill above could not name, and
    # nothing can reach it. Deleting a title takes its seasons and episodes with
    # it, and a watch holds the key rather than the row, so a watch of a row
    # with no key never existed to be orphaned.
    op.execute("DELETE FROM canonicalepisode WHERE key IS NULL")
    op.execute("DELETE FROM canonicalseason WHERE key IS NULL")
    op.execute("DELETE FROM canonicalshow WHERE key IS NULL")

    # Titles first, so a season merged below is already under the title that
    # survived rather than one about to be deleted.
    op.execute(_SHOW_DUPLICATES)
    op.execute(
        "UPDATE show SET canonical_show_id = merged_shows.kept "
        "FROM merged_shows WHERE show.canonical_show_id = merged_shows.dropped",
    )
    op.execute(
        "UPDATE canonicalseason SET canonical_show_id = merged_shows.kept "
        "FROM merged_shows "
        "WHERE canonicalseason.canonical_show_id = merged_shows.dropped",
    )
    op.execute(
        "DELETE FROM canonicalshow USING merged_shows "
        "WHERE canonicalshow.id = merged_shows.dropped "
        "AND merged_shows.dropped <> merged_shows.kept",
    )

    op.execute(_SEASON_DUPLICATES)
    op.execute(
        "UPDATE season SET canonical_season_id = merged_seasons.kept "
        "FROM merged_seasons "
        "WHERE season.canonical_season_id = merged_seasons.dropped",
    )
    op.execute(
        "UPDATE canonicalepisode SET canonical_season_id = merged_seasons.kept "
        "FROM merged_seasons "
        "WHERE canonicalepisode.canonical_season_id = merged_seasons.dropped",
    )
    op.execute(
        "DELETE FROM canonicalseason USING merged_seasons "
        "WHERE canonicalseason.id = merged_seasons.dropped "
        "AND merged_seasons.dropped <> merged_seasons.kept",
    )

    op.execute(_EPISODE_DUPLICATES)
    op.execute(
        "UPDATE episode SET canonical_episode_id = merged_episodes.kept "
        "FROM merged_episodes "
        "WHERE episode.canonical_episode_id = merged_episodes.dropped",
    )
    op.execute(
        "DELETE FROM canonicalepisode USING merged_episodes "
        "WHERE canonicalepisode.id = merged_episodes.dropped "
        "AND merged_episodes.dropped <> merged_episodes.kept",
    )

    op.execute("DROP TABLE merged_shows")
    op.execute("DROP TABLE merged_seasons")
    op.execute("DROP TABLE merged_episodes")

    for table, constraint, columns in _UNIQUE_KEYS:
        op.alter_column(table, "key", existing_type=sa.String(), nullable=False)
        op.create_unique_constraint(constraint, table, columns)


def downgrade():
    for table in ("canonicalshow", "canonicalseason", "canonicalepisode"):
        op.alter_column(table, "key", existing_type=sa.String(), nullable=True)
