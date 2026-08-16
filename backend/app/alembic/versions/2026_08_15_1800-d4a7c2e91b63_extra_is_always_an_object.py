"""extra is always an object

`extra` was a text column each plugin wrote whatever it liked into, which worked
while only one thing was ever said in it. TMDB says two now - the episode order a
title is read in, beside whatever comes later - and a column holding one bare
string has no room for a second without deciding what the first one now means.

Every `extra` becomes a `jsonb` object, never null. The database enforces the
shape, what is stored can be read back with `->>` rather than only by whoever
wrote it, and a plugin adding a second thing adds a key.

The one column with anything in it is `file`, where four plugins mark a file they
have read to the end with the bare string "Completed". That becomes
`{"status": "Completed"}`. Anything else already holding a JSON object is kept as
it is, and anything else at all is wrapped the same way rather than thrown away,
since `extra` is the plugin's own column and this migration is not the place to
decide something in it was rubbish.

`file` is the biggest table here - it holds every response ever downloaded - and
changing a column's type rewrites the table, so this one is slow and takes a lock
while it runs.

Revision ID: d4a7c2e91b63
Revises: c3d9e5a71f42
Create Date: 2026-08-15 18:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4a7c2e91b63"
down_revision = "c3d9e5a71f42"
branch_labels = None
depends_on = None

_TABLES = ("episode", "file", "plugin", "season", "show", "source")

# Anything already an object is kept, and anything else is wrapped rather than
# guessed at. Written as a function with its own exception block because
# Postgres has no cast that answers "not valid JSON" with anything but an error,
# and one row of something unreadable would otherwise take the whole migration
# down.
_READER = """
CREATE FUNCTION _extra_to_jsonb(value text) RETURNS jsonb AS $$
BEGIN
    IF value IS NULL OR btrim(value) = '' THEN
        RETURN '{}'::jsonb;
    END IF;
    BEGIN
        -- Concatenating onto an empty object is what rejects a valid JSON value
        -- that is not an object, such as a bare number or a list.
        RETURN '{}'::jsonb || value::jsonb;
    EXCEPTION WHEN others THEN
        RETURN jsonb_build_object('status', value);
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

# Going back, an object holding nothing is the column saying nothing, and one
# holding only the mark this migration wrote is unwrapped to the bare string it
# came from. Anything else is written out as the JSON it is, so nothing a plugin
# stored while the column was an object is lost by going back.
_WRITER = """
CREATE FUNCTION _extra_to_text(value jsonb) RETURNS text AS $$
BEGIN
    IF value IS NULL OR value = '{}'::jsonb THEN
        RETURN NULL;
    END IF;
    IF (SELECT count(*) FROM jsonb_object_keys(value)) = 1
       AND value ? 'status'
       AND jsonb_typeof(value -> 'status') = 'string' THEN
        RETURN value ->> 'status';
    END IF;
    RETURN value::text;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""


def upgrade() -> None:
    op.execute(_READER)
    for table in _TABLES:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN extra '
            f"TYPE jsonb USING _extra_to_jsonb(extra)",
        )
        op.execute(f"ALTER TABLE \"{table}\" ALTER COLUMN extra SET DEFAULT '{{}}'")
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN extra SET NOT NULL')
    op.execute("DROP FUNCTION _extra_to_jsonb(text)")


def downgrade() -> None:
    op.execute(_WRITER)
    for table in _TABLES:
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN extra DROP NOT NULL')
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN extra DROP DEFAULT')
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN extra '
            f"TYPE varchar USING _extra_to_text(extra)",
        )
    op.execute("DROP FUNCTION _extra_to_text(jsonb)")
