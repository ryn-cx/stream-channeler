"""make the canonical rows the only account of what media is

The identifier strings were doing three jobs: grouping two websites' copies into
one work, pointing at TMDB, and standing in as a per-source fallback key. The
canonical tables now do the first two and the record's own `key` does the third,
so the strings go.

TMDB stops being ordinary media at the same time. Its `Source`, `Show`, `Season`
and `Episode` rows are deleted -- what it holds now lives in the canonical
tables, written there by `plugins/TMDB/upsert.py`. The `Plugin` row stays,
because it still owns the `File` response cache the downloads read through.

Irreversible, and destructive by design: a copy that never reached a canonical
row has nothing to be a copy of and is deleted rather than left pointing at
nothing, since the pointers become `NOT NULL` here.

Revision ID: f2a7c8e4b593
Revises: e9b4c6d2f371
Create Date: 2026-08-11 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f2a7c8e4b593"
down_revision = "e9b4c6d2f371"
branch_labels = None
depends_on = None

# Each copy table, its canonical pointer, and the indexes built on the
# identifier that pointer replaces.
LEVELS = (
    (
        "show",
        "canonical_show_id",
        "show_identifier",
        ("Show-show_identifier-index", "Show-live-show_identifier-index"),
    ),
    (
        "season",
        "canonical_season_id",
        "season_identifier",
        ("Season-season_identifier-index", "Season-live-season_identifier-index"),
    ),
    (
        "episode",
        "canonical_episode_id",
        "episode_identifier",
        ("Episode-episode_identifier-index", "Episode-live-episode_identifier-index"),
    ),
)


def upgrade():
    # TMDB's media was only ever standing in for what a website left out, which
    # the canonical rows now hold directly. Deleting the source cascades to its
    # shows, seasons and episodes; the plugin row is left alone.
    op.execute(
        """
        DELETE FROM source
        USING plugin
        WHERE plugin.id = source.plugin_id AND plugin.key = 'TMDB'
        """,
    )

    # Anything still pointing at nothing is a copy of nothing. Deleted deepest
    # first so a parent's children go before the parent does.
    op.execute("DELETE FROM episode WHERE canonical_episode_id IS NULL")
    op.execute("DELETE FROM season WHERE canonical_season_id IS NULL")
    op.execute("DELETE FROM show WHERE canonical_show_id IS NULL")
    op.execute("DELETE FROM watch WHERE canonical_episode_id IS NULL")

    for table, canonical, identifier, indexes in LEVELS:
        for index in indexes:
            op.drop_index(index, table_name=table)
        op.drop_column(table, identifier)
        op.alter_column(table, canonical, existing_type=sa.Uuid(), nullable=False)

    op.alter_column(
        "watch",
        "canonical_episode_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_index("Watch-episode_identifier-index", table_name="watch")
    op.drop_constraint(
        "Watch-user_id-episode_identifier-watch_date-key",
        "watch",
        type_="unique",
    )
    op.drop_column("watch", "episode_identifier")
    # The partial index the nullable pointer needed becomes a plain unique one,
    # now that every watch names an episode.
    op.drop_index(
        "Watch-user_id-canonical_episode_id-watch_date-key", table_name="watch"
    )
    op.create_index(
        "Watch-user_id-canonical_episode_id-watch_date-key",
        "watch",
        ["user_id", "canonical_episode_id", "watch_date"],
        unique=True,
    )

    # The lock and the note describe this copy's link decision, which is now a
    # pointer rather than a string, so they are named for what they describe.
    op.alter_column(
        "show", "show_identifier_locked", new_column_name="canonical_show_locked"
    )
    op.add_column("show", sa.Column("canonical_show_note", sa.String(), nullable=True))
    op.alter_column(
        "episode",
        "episode_identifier_locked",
        new_column_name="canonical_episode_locked",
    )
    op.alter_column(
        "episode",
        "episode_identifier_note",
        new_column_name="canonical_episode_note",
    )

    # A copy names one episode at most, within the season holding it. The
    # show-wide rule this stands in for is still Python's to keep, since an
    # `Episode` has no `show_id` to constrain on.
    op.create_index(
        "Episode-live-season_id-canonical_episode_id-key",
        "episode",
        ["season_id", "canonical_episode_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade():
    message = (
        "Irreversible: the identifier strings and TMDB's own media rows are gone, "
        "and nothing left records what they said."
    )
    raise RuntimeError(message)
