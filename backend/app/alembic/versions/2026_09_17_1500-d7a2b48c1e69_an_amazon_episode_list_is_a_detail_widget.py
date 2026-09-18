"""an amazon episode list is a detail widget

The Amazon file holding a page of a season's episodes was keyed by the name of
the class that downloads it, `EpisodeList`, and is now keyed `DetailWidgets`
after the endpoint it comes from.

Revision ID: d7a2b48c1e69
Revises: c6f1a8d3e527
Create Date: 2026-09-17 15:00:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "d7a2b48c1e69"
down_revision = "c6f1a8d3e527"
branch_labels = None
depends_on = None


def _amazon_plugin_id(connection: sa.Connection) -> uuid.UUID | None:
    return connection.execute(
        sa.text("SELECT id FROM plugin WHERE key = 'Amazon'"),
    ).scalar_one_or_none()


def _rename(
    connection: sa.Connection,
    plugin_id: uuid.UUID,
    old_key: str,
    new_key: str,
) -> None:
    old_prefix = f"{old_key}/"
    connection.execute(
        sa.text("""
            UPDATE file
            SET key = :new_prefix || right(key, -:old_prefix_length)
            WHERE plugin_id = :plugin_id
              AND key LIKE :old_prefix || '%'
        """),
        {
            "plugin_id": plugin_id,
            "old_prefix": old_prefix,
            "old_prefix_length": len(old_prefix),
            "new_prefix": f"{new_key}/",
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    plugin_id = _amazon_plugin_id(connection)
    if plugin_id is None:
        return
    _rename(connection, plugin_id, "EpisodeList", "DetailWidgets")


def downgrade() -> None:
    connection = op.get_bind()
    plugin_id = _amazon_plugin_id(connection)
    if plugin_id is None:
        return
    _rename(connection, plugin_id, "DetailWidgets", "EpisodeList")
