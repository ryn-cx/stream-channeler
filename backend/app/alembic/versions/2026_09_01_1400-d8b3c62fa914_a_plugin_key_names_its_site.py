"""a plugin key names its site

A plugin's key used to be the name of the class implementing it - `AdultSwim`,
`ParamountPlus`, `WatchMode` - and is now the plain text name of the site the
plugin supports: `Adult Swim`, `Paramount+`, `Watchmode`.

Both keys can already be present, one row written before the rename and one
after. The two are combined into the plain text row: its sources and files are
kept, the class named row's sources and files move over, and where the two hold
the same key the plain text row's child wins and the other is dropped along with
everything under it.

Revision ID: d8b3c62fa914
Revises: c7a4e91b62d5
Create Date: 2026-09-01 14:00:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "d8b3c62fa914"
down_revision = "c7a4e91b62d5"
branch_labels = None
depends_on = None

RENAMES = [
    ("AdultSwim", "Adult Swim"),
    ("Amazon", "Amazon Prime Video"),
    ("DisneyPlus", "Disney+"),
    ("HBOMax", "HBO Max"),
    ("HiDive", "HIDIVE"),
    ("NHKWorld", "NHK World"),
    ("ParamountPlus", "Paramount+"),
    ("Pluto", "Pluto TV"),
    ("Roku", "The Roku Channel"),
    ("StreamChanneler", "Stream Channeler"),
    ("WatchMode", "Watchmode"),
]


def _plugin_id(connection: sa.Connection, key: str) -> uuid.UUID | None:
    return connection.execute(
        sa.text("SELECT id FROM plugin WHERE key = :key"),
        {"key": key},
    ).scalar_one_or_none()


def _merge(connection: sa.Connection, old_id: uuid.UUID, new_id: uuid.UUID) -> None:
    for table in ("source", "file"):
        connection.execute(
            sa.text(f"""
                DELETE FROM {table} AS old_child
                USING {table} AS new_child
                WHERE old_child.plugin_id = :old_id
                  AND new_child.plugin_id = :new_id
                  AND new_child.key = old_child.key
            """),  # noqa: S608
            {"old_id": old_id, "new_id": new_id},
        )
        connection.execute(
            sa.text(f"""
                UPDATE {table} SET plugin_id = :new_id WHERE plugin_id = :old_id
            """),  # noqa: S608
            {"old_id": old_id, "new_id": new_id},
        )
    connection.execute(
        sa.text("DELETE FROM plugin WHERE id = :old_id"),
        {"old_id": old_id},
    )


def upgrade() -> None:
    connection = op.get_bind()
    for old_key, new_key in RENAMES:
        old_id = _plugin_id(connection, old_key)
        if old_id is None:
            continue

        new_id = _plugin_id(connection, new_key)
        if new_id is None:
            connection.execute(
                sa.text("UPDATE plugin SET key = :new_key WHERE id = :old_id"),
                {"new_key": new_key, "old_id": old_id},
            )
        else:
            _merge(connection, old_id, new_id)


def downgrade() -> None:
    connection = op.get_bind()
    for old_key, new_key in RENAMES:
        connection.execute(
            sa.text("UPDATE plugin SET key = :old_key WHERE key = :new_key"),
            {"old_key": old_key, "new_key": new_key},
        )
