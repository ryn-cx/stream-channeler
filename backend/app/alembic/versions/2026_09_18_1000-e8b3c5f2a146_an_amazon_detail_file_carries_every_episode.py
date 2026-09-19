"""an amazon detail file carries every episode

The Amazon detail file held the page as it was served and the rest of a
season's episodes were downloaded into a `DetailWidgets` file of their own. A
detail file now holds the page together with every remaining page of its
episode list, so the old content of both is dropped and downloaded again.

Revision ID: e8b3c5f2a146
Revises: d7a2b48c1e69
Create Date: 2026-09-18 10:00:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "e8b3c5f2a146"
down_revision = "d7a2b48c1e69"
branch_labels = None
depends_on = None


def _amazon_plugin_id(connection: sa.Connection) -> uuid.UUID | None:
    return connection.execute(
        sa.text("SELECT id FROM plugin WHERE key = 'Amazon'"),
    ).scalar_one_or_none()


def _delete(connection: sa.Connection, plugin_id: uuid.UUID, class_key: str) -> None:
    connection.execute(
        sa.text("""
            DELETE FROM file
            WHERE plugin_id = :plugin_id
              AND key LIKE :prefix || '%'
        """),
        {"plugin_id": plugin_id, "prefix": f"{class_key}/"},
    )


def upgrade() -> None:
    connection = op.get_bind()
    plugin_id = _amazon_plugin_id(connection)
    if plugin_id is None:
        return
    _delete(connection, plugin_id, "DetailWidgets")
    _delete(connection, plugin_id, "Detail")


def downgrade() -> None:
    connection = op.get_bind()
    plugin_id = _amazon_plugin_id(connection)
    if plugin_id is None:
        return
    _delete(connection, plugin_id, "Detail")
