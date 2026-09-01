"""a record says its own status

`status` was a field inside `extra`, the object each plugin writes whatever it
likes into. Every record already carries one - a file read to the end, a plugin
part way through being set up, a season with new episodes waiting - so it becomes
a column of its own on all six tables and is read and written like any other.

Three shapes of `extra` are found on the way. An object holding `status` gives up
that field and keeps the rest. A bare string is a status written before `extra`
was an object at all - "Invalid unique_identifier ..." and its like - and becomes
the column outright. Everything else, including the JSON `null` most files hold,
becomes the empty object `extra` is supposed to be, so nothing reading it has to
answer for a null again.

Revision ID: c7a4e91b62d5
Revises: b4d9f27ac513
Create Date: 2026-09-01 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "c7a4e91b62d5"
down_revision = "b4d9f27ac513"
branch_labels = None
depends_on = None

_TABLES = ("episode", "file", "plugin", "season", "show", "source")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("status", sa.String(), nullable=True))
        op.execute(
            f"""
            UPDATE "{table}"
            SET status = CASE jsonb_typeof(extra)
                    WHEN 'object' THEN extra ->> 'status'
                    WHEN 'string' THEN extra #>> '{{}}'
                END,
                extra = CASE jsonb_typeof(extra)
                    WHEN 'object' THEN extra - 'status'
                    ELSE '{{}}'::jsonb
                END
            """,
        )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"""
            UPDATE "{table}"
            SET extra = extra || jsonb_build_object('status', status)
            WHERE status IS NOT NULL
            """,
        )
        op.drop_column(table, "status")
