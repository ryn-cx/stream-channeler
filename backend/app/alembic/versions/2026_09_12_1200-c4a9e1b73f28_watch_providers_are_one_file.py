"""watch providers are one file

Revision ID: c4a9e1b73f28
Revises: b7f3c05a26d9
Create Date: 2026-09-12 12:00:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "c4a9e1b73f28"
down_revision = "b7f3c05a26d9"
branch_labels = None
depends_on = None

ANY_KEY = r"^(Movies|TV Series|TV Seasons)/Watch Providers/"
DATED_KEY = r"^(Movies|TV Series|TV Seasons)/Watch Providers/.+/\d{4}-\d{2}-\d{2}\.json$"
UNDATED_KEY = r"^(Movies|TV Series|TV Seasons)/Watch Providers/.+\.json$"
DATE_SUFFIX = r"/\d{4}-\d{2}-\d{2}\.json$"


def _tmdb_plugin_id(connection: sa.Connection) -> uuid.UUID | None:
    return connection.execute(
        sa.text("SELECT id FROM plugin WHERE key = 'TMDB'"),
    ).scalar_one_or_none()


def upgrade() -> None:
    connection = op.get_bind()
    plugin_id = _tmdb_plugin_id(connection)
    if plugin_id is None:
        return
    parameters = {
        "plugin_id": plugin_id,
        "any_key": ANY_KEY,
        "dated_key": DATED_KEY,
        "date_suffix": DATE_SUFFIX,
    }
    connection.execute(
        sa.text("""
            DELETE FROM file
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT
                        id,
                        row_number() OVER (
                            PARTITION BY
                                regexp_replace(key, :date_suffix, '.json')
                            ORDER BY data_timestamp DESC, id DESC
                        ) AS position
                    FROM file
                    WHERE plugin_id = :plugin_id
                      AND key ~ :any_key
                ) AS ranked
                WHERE position > 1
            )
        """),
        parameters,
    )
    connection.execute(
        sa.text("""
            UPDATE file
            SET key = regexp_replace(key, :date_suffix, '.json'),
                status = NULL,
                update_at = NULL
            WHERE plugin_id = :plugin_id
              AND key ~ :dated_key
        """),
        parameters,
    )


def downgrade() -> None:
    connection = op.get_bind()
    plugin_id = _tmdb_plugin_id(connection)
    if plugin_id is None:
        return
    connection.execute(
        sa.text("""
            UPDATE file
            SET key = left(key, -5)
                || '/'
                || to_char(data_timestamp, 'YYYY-MM-DD')
                || '.json',
                status = 'Incomplete'
            WHERE plugin_id = :plugin_id
              AND key ~ :undated_key
              AND key !~ :dated_key
        """),
        {
            "plugin_id": plugin_id,
            "undated_key": UNDATED_KEY,
            "dated_key": DATED_KEY,
        },
    )
