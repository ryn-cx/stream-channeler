"""a watch names the plugin as well as the key

A watch was matched to an episode on the key alone, which worked only for as long
as a key carried the name of whoever issued it. Keys are the websites' own ids
now, so the name has come off them, and on the key alone a Crunchyroll episode
whose id happens to read like a YouTube video id is watched whenever that video
is.

The pair is what names the media: who issued a key, and the key. So the plugin is
written onto the episode - it cannot be reached across a join from a generated
column, and an episode never moves between plugins, so the copy cannot go stale -
and the pair is generated from it into `watch_identifier`, which is what a watch
now holds and what every read joins on.

Nothing is lost by matching on the pair rather than on the key. A key is still
carried by every listing of the same media - one YouTube video is under a
channel's uploads, under each playlist holding it, and under itself - so one watch
still marks all of them, which is why neither index here is unique.

Revision ID: c4f2b9e73a18
Revises: b6e4a2c9d713
Create Date: 2026-08-14 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4f2b9e73a18"
down_revision = "b6e4a2c9d713"
branch_labels = None
depends_on = None

_BACKFILL_PLUGIN_KEY = """
    UPDATE episode
    SET plugin_key = plugin.key
    FROM season, show, source, plugin
    WHERE season.id = episode.season_id
      AND show.id = season.show_id
      AND source.id = show.source_id
      AND plugin.id = source.plugin_id
"""

# An episode reaches its plugin through four non-nullable foreign keys, so a row
# left without one is a row the chain does not hold, and generating an identifier
# for it would be inventing who wrote it.
_PLUGIN_KEY_CHECK = """
    DO $$
    DECLARE offending int;
    BEGIN
        SELECT count(*) INTO offending FROM episode WHERE plugin_key IS NULL;
        IF offending > 0 THEN
            RAISE EXCEPTION '% episodes reach no plugin', offending;
        END IF;
    END $$
"""

# The episode a watch names, where this database still holds it. Read off the
# generated column rather than rebuilt here, so the two cannot disagree - which
# matters for TMDB, whose keys already begin with its name and so are prefixed
# with it a second time.
_BACKFILL_FROM_EPISODE = """
    UPDATE watch
    SET watch_identifier = episode.watch_identifier
    FROM episode
    WHERE episode.key = watch.canonical_episode_key
      AND episode.canonical_episode_id IS NULL
"""

# What is left is a watch of an episode this database no longer holds under that
# key, which is every watch written while the plugin's name was still on the key.
# That old key is `<plugin> <key>` already - it is what the identifier is built to
# be - so it carries across as it stands rather than being resolved.
_BACKFILL_FROM_OLD_KEY = """
    UPDATE watch
    SET watch_identifier = canonical_episode_key
    WHERE watch_identifier IS NULL
"""

_WATCH_IDENTIFIER_CHECK = """
    DO $$
    DECLARE offending int;
    BEGIN
        SELECT count(*) INTO offending FROM watch WHERE watch_identifier IS NULL;
        IF offending > 0 THEN
            RAISE EXCEPTION '% watches name no episode', offending;
        END IF;
    END $$
"""

# The reverse: the key of the episode the identifier names, where it is held.
_RESTORE_FROM_EPISODE = """
    UPDATE watch
    SET canonical_episode_key = episode.key
    FROM episode
    WHERE episode.watch_identifier = watch.watch_identifier
      AND episode.canonical_episode_id IS NULL
"""

_RESTORE_FROM_IDENTIFIER = """
    UPDATE watch
    SET canonical_episode_key = watch_identifier
    WHERE canonical_episode_key IS NULL
"""


def upgrade() -> None:
    op.add_column("episode", sa.Column("plugin_key", sa.String(), nullable=True))
    op.execute(_BACKFILL_PLUGIN_KEY)
    op.execute(_PLUGIN_KEY_CHECK)
    op.alter_column("episode", "plugin_key", existing_type=sa.String(), nullable=False)

    # Postgres computes a stored column for every existing row as it is added, so
    # the plugin has to be there first or every identifier would be NULL.
    op.execute(
        "ALTER TABLE episode ADD COLUMN watch_identifier text"
        " GENERATED ALWAYS AS (plugin_key || ' ' || \"key\") STORED NOT NULL",
    )
    op.create_index(
        "Episode-canonical-watch_identifier-index",
        "episode",
        ["watch_identifier"],
        unique=False,
        postgresql_where=sa.text("canonical_episode_id IS NULL"),
    )

    op.add_column("watch", sa.Column("watch_identifier", sa.String(), nullable=True))
    op.execute(_BACKFILL_FROM_EPISODE)
    op.execute(_BACKFILL_FROM_OLD_KEY)
    op.execute(_WATCH_IDENTIFIER_CHECK)
    op.alter_column(
        "watch", "watch_identifier", existing_type=sa.String(), nullable=False
    )

    op.drop_index("Watch-canonical_episode_key-index", table_name="watch")
    op.drop_index(
        "Watch-user_id-canonical_episode_key-watch_date-key", table_name="watch"
    )
    op.drop_column("watch", "canonical_episode_key")
    op.create_index(
        "Watch-watch_identifier-index",
        "watch",
        ["watch_identifier"],
        unique=False,
    )
    op.create_index(
        "Watch-user_id-watch_identifier-watch_date-key",
        "watch",
        ["user_id", "watch_identifier", "watch_date"],
        unique=True,
    )


def downgrade() -> None:
    op.add_column(
        "watch",
        sa.Column("canonical_episode_key", sa.String(), nullable=True),
    )
    op.execute(_RESTORE_FROM_EPISODE)
    op.execute(_RESTORE_FROM_IDENTIFIER)
    op.alter_column(
        "watch",
        "canonical_episode_key",
        existing_type=sa.String(),
        nullable=False,
    )

    op.drop_index("Watch-user_id-watch_identifier-watch_date-key", table_name="watch")
    op.drop_index("Watch-watch_identifier-index", table_name="watch")
    op.drop_column("watch", "watch_identifier")
    op.create_index(
        "Watch-canonical_episode_key-index",
        "watch",
        ["canonical_episode_key"],
        unique=False,
    )
    op.create_index(
        "Watch-user_id-canonical_episode_key-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_key", "watch_date"],
        unique=True,
    )

    op.drop_index("Episode-canonical-watch_identifier-index", table_name="episode")
    op.drop_column("episode", "watch_identifier")
    op.drop_column("episode", "plugin_key")
