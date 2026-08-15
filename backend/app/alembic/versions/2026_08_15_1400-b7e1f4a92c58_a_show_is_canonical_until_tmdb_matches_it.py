"""a show is canonical until tmdb matches it

`f2c6a9d41b87` gave every show TMDB has no match for a canonical show of its own,
keyed by the plugin's key ahead of the show's, so the shows of one plugin met on
one row. That row says nothing the shows under it do not say already, and writing
it means a second upsert on every import.

A show TMDB has no match for is the canonical show instead, which is what it
already is when it is written. Every plugin-keyed canonical show is dropped, and
each show linked to one is canonical again.

Only the plugin-keyed rows go. A show linked to a TMDB canonical show keeps that
link and stays non-canonical.

Revision ID: b7e1f4a92c58
Revises: f2c6a9d41b87
Create Date: 2026-08-15 14:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b7e1f4a92c58"
down_revision = "f2c6a9d41b87"
branch_labels = None
depends_on = None

# `Show-canonical-key-key` held one canonical show per key across every source.
# That was what the plugin-keyed row satisfied: a plugin offering one show
# through several sources writes a row per source under the same key, and they
# all pointed at that one row. Each of them is canonical now, so a key is carried
# by as many canonical shows as there are sources offering it, and the index is
# rebuilt without the constraint. It is dropped before anything is made canonical
# again, since making them canonical is what would breach it.
_DROP_UNIQUE_KEY = """
DROP INDEX IF EXISTS "Show-canonical-key-key"
"""

_KEY_INDEX = """
CREATE INDEX IF NOT EXISTS "Show-canonical-key-index"
ON show (key) WHERE is_canonical IS TRUE
"""

# The canonical shows written for want of a TMDB match, which carry the key of
# the plugin that wrote them ahead of the show's own.
_PLUGIN_KEYED = """
CREATE TEMP TABLE plugin_keyed ON COMMIT DROP AS
SELECT canonical.id AS canonical_show_id
FROM show AS canonical
JOIN source ON source.id = canonical.source_id
JOIN plugin ON plugin.id = source.plugin_id
WHERE canonical.is_canonical
  AND canonical.key LIKE plugin.key || ' %'
"""

# The shows linked to one, which are canonical again once the link is gone. A
# show linked to a TMDB canonical show as well keeps that link and stays a copy.
_RESTORE = """
UPDATE show
SET is_canonical = TRUE
WHERE id IN (
    SELECT link.show_id
    FROM showcanonicalshow AS link
    JOIN plugin_keyed ON plugin_keyed.canonical_show_id = link.canonical_show_id
)
AND NOT EXISTS (
    SELECT 1
    FROM showcanonicalshow AS other
    WHERE other.show_id = show.id
      AND other.canonical_show_id NOT IN (
          SELECT canonical_show_id FROM plugin_keyed
      )
)
"""

_UNLINK = """
DELETE FROM showcanonicalshow
USING plugin_keyed
WHERE showcanonicalshow.canonical_show_id = plugin_keyed.canonical_show_id
"""

_DROP = """
DELETE FROM show
USING plugin_keyed
WHERE show.id = plugin_keyed.canonical_show_id
"""

# The rule the move is for: nothing is a copy of a row that is itself a copy.
_DEPTH_CHECK = """
DO $$
DECLARE
    wrong bigint;
BEGIN
    SELECT count(*) INTO wrong
    FROM show
    WHERE EXISTS (
              SELECT 1 FROM showcanonicalshow
              WHERE showcanonicalshow.canonical_show_id = show.id
          )
      AND EXISTS (
              SELECT 1 FROM showcanonicalshow
              WHERE showcanonicalshow.show_id = show.id
          );
    IF wrong > 0 THEN
        RAISE EXCEPTION '% shows are a copy and a canonical show at once', wrong;
    END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(_PLUGIN_KEYED)
    op.execute(_DROP_UNIQUE_KEY)
    op.execute(_KEY_INDEX)
    op.execute(_RESTORE)
    op.execute(_UNLINK)
    op.execute(_DROP)
    op.execute(_DEPTH_CHECK)


def downgrade() -> None:
    # Only the index is undone here. The rows are `f2c6a9d41b87`'s, written from
    # the shows under them, so putting them back is running that again rather
    # than anything of this migration's own - and the unique index cannot come
    # back until it has, since it is the rows that make one key one show.
    op.execute('DROP INDEX IF EXISTS "Show-canonical-key-index"')
