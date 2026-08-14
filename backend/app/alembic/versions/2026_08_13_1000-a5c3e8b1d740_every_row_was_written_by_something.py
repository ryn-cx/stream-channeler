"""every row was written by something

A title had no source, on the reading that a title is not carried anywhere and so
is on no website. The reading did not survive contact with the importer: TMDB
writes its titles against its own source and always has, so the column was already
set on every title TMDB catalogued and absent only on the ones minted for a
listing to point at.

A title is written by a plugin the same way a listing is, and the minted ones say
which plugin in their own key. So they are given the source of the plugin that
minted them, the column stops being absent, and `is_canonical` is left as the
whole of what tells a title from a listing.

Revision ID: a5c3e8b1d740
Revises: c7e1a4b8d635
Create Date: 2026-08-13 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a5c3e8b1d740"
down_revision = "c7e1a4b8d635"
branch_labels = None
depends_on = None

# A plugin whose sources are all named after websites - a provider list, a
# catalogue split in two - has none standing for the plugin itself, and that is
# the one the titles it mints belong to. Which plugin minted a title is the first
# word of its key, since that is what `record_key` puts there.
_MINT_PLUGIN_SOURCES = """
    INSERT INTO source (id, created_at, modified_at, key, name, plugin_id)
    SELECT DISTINCT ON (plugin.id)
           gen_random_uuid(), now(), now(), plugin.key, plugin.name, plugin.id
    FROM show
    JOIN plugin ON plugin.key = split_part(show.key, ' ', 1)
    WHERE show.source_id IS NULL
      AND NOT EXISTS (
          SELECT 1 FROM source
          WHERE source.plugin_id = plugin.id
            AND source.key = plugin.key
      )
"""

_BACKFILL_SOURCE = """
    UPDATE show
    SET source_id = source.id
    FROM plugin
    JOIN source ON source.plugin_id = plugin.id AND source.key = plugin.key
    WHERE show.source_id IS NULL
      AND plugin.key = split_part(show.key, ' ', 1)
"""

# A title whose key names no plugin is a row nothing can be said to have written,
# and inventing a source for it would be saying something anyway.
_SOURCE_CHECK = """
    DO $$
    DECLARE offending int;
    BEGIN
        SELECT count(*) INTO offending FROM show WHERE source_id IS NULL;
        IF offending > 0 THEN
            RAISE EXCEPTION
                '% shows name no source and no plugin their key belongs to',
                offending;
        END IF;
    END $$
"""


def upgrade() -> None:
    op.execute(_MINT_PLUGIN_SOURCES)
    op.execute(_BACKFILL_SOURCE)
    op.execute(_SOURCE_CHECK)

    op.alter_column("show", "source_id", existing_type=sa.Uuid(), nullable=False)

    # The rule held for the rows that had a source and said nothing about the rows
    # that did not. Every row has one now, so it is a rule over all of them and is
    # written as the constraint it always meant to be.
    op.drop_index("Show-source_id-key-key", table_name="show")
    op.create_unique_constraint(
        "Show-source_id-key-key",
        "show",
        ["source_id", "key"],
    )


def downgrade() -> None:
    op.drop_constraint("Show-source_id-key-key", "show", type_="unique")
    op.alter_column("show", "source_id", existing_type=sa.Uuid(), nullable=True)

    # Only the minted titles had no source. TMDB's had one before this and keep
    # it, and they are the titles whose keys TMDB issued.
    op.execute(
        """
        UPDATE show
        SET source_id = NULL
        WHERE is_canonical IS TRUE
          AND key NOT LIKE 'TMDB %'
        """,
    )
    op.execute(
        'CREATE UNIQUE INDEX "Show-source_id-key-key" ON show (source_id, key)'
        " WHERE source_id IS NOT NULL",
    )
