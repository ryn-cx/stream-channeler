"""a tmdb file is named for its endpoint

A TMDB file used to be keyed by the name of the class that downloads it -
`ShowDetail`, `TvWatchProviders`, `SeasonDetail` - and is now keyed by the TMDB
endpoint it comes from: `TV Series/Details`, `TV Series/Watch Providers`,
`TV Seasons/Details`.

`ShowDetail` and `TvSeriesDetails` both held the tv series details endpoint and
now share one key. Where both hold the same title the `ShowDetail` row wins and
the other is dropped.

Revision ID: f0d6b83e4a71
Revises: e9c5a71d3f60
Create Date: 2026-09-03 10:00:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "f0d6b83e4a71"
down_revision = "e9c5a71d3f60"
branch_labels = None
depends_on = None

RENAMES = [
    ("MovieDetails", "Movies/Details"),
    ("MovieTranslations", "Movies/Translations"),
    ("MovieWatchProviders", "Movies/Watch Providers"),
    ("ShowDetail", "TV Series/Details"),
    ("TvSeriesDetails", "TV Series/Details"),
    ("TvWatchProviders", "TV Series/Watch Providers"),
    ("ShowImages", "TV Series/Images"),
    ("EpisodeGroups", "TV Series/Episode Groups"),
    ("ShowChanges", "TV Series/Changes"),
    ("SeasonDetail", "TV Seasons/Details"),
    ("SeasonWatchProviders", "TV Seasons/Watch Providers"),
    ("EpisodeDetail", "TV Episodes/Details"),
    ("EpisodeTranslations", "TV Episodes/Translations"),
    ("EpisodeGroupDetail", "TV Episode Groups/Details"),
    ("MultiSearch", "Search/Multi"),
    ("MovieSearch", "Search/Movie"),
    ("TvSearch", "Search/TV"),
]


def _tmdb_plugin_id(connection: sa.Connection) -> uuid.UUID | None:
    return connection.execute(
        sa.text("SELECT id FROM plugin WHERE key = 'TMDB'"),
    ).scalar_one_or_none()


def _rename(
    connection: sa.Connection,
    plugin_id: uuid.UUID,
    old_key: str,
    new_key: str,
) -> None:
    old_prefix = f"{old_key}/"
    parameters = {
        "plugin_id": plugin_id,
        "old_prefix": old_prefix,
        "old_prefix_length": len(old_prefix),
        "new_prefix": f"{new_key}/",
    }
    connection.execute(
        sa.text("""
            DELETE FROM file AS old_file
            USING file AS new_file
            WHERE old_file.plugin_id = :plugin_id
              AND new_file.plugin_id = :plugin_id
              AND old_file.key LIKE :old_prefix || '%'
              AND new_file.key = :new_prefix
                || right(old_file.key, -:old_prefix_length)
        """),
        parameters,
    )
    connection.execute(
        sa.text("""
            UPDATE file
            SET key = :new_prefix || right(key, -:old_prefix_length)
            WHERE plugin_id = :plugin_id
              AND key LIKE :old_prefix || '%'
        """),
        parameters,
    )


def upgrade() -> None:
    connection = op.get_bind()
    plugin_id = _tmdb_plugin_id(connection)
    if plugin_id is None:
        return
    for old_key, new_key in RENAMES:
        _rename(connection, plugin_id, old_key, new_key)


def downgrade() -> None:
    connection = op.get_bind()
    plugin_id = _tmdb_plugin_id(connection)
    if plugin_id is None:
        return
    for old_key, new_key in RENAMES:
        if old_key == "TvSeriesDetails":
            continue
        _rename(connection, plugin_id, new_key, old_key)
