# TODO: Validate
"""The plugin Amazon is read by is named Amazon.

A row keyed Amazon can already be there, written by the renamed code before this
ran and holding nothing but the records an initialization makes. The row that
holds the titles is the one kept: whatever the empty row has that the kept row
does not is moved over, and the empty row is dropped along with the rest.
"""

from alembic import op

revision = "b5e7c210d934"
down_revision = "a8c4d1e6b972"
branch_labels = None
depends_on = None


_RENAME_SOURCE = """
    UPDATE source
    SET key = 'Amazon'
    FROM plugin
    WHERE plugin.id = source.plugin_id
      AND plugin.key = 'Amazon Prime Video'
      AND source.key = 'Amazon Prime Video'
"""

_ADOPT_SOURCES = """
    UPDATE source
    SET plugin_id = kept.id
    FROM plugin AS placeholder, plugin AS kept
    WHERE source.plugin_id = placeholder.id
      AND placeholder.key = 'Amazon'
      AND kept.key = 'Amazon Prime Video'
      AND NOT EXISTS (
          SELECT 1
          FROM source AS existing
          WHERE existing.plugin_id = kept.id
            AND existing.key = source.key
      )
"""

_ADOPT_FILES = """
    UPDATE file
    SET plugin_id = kept.id
    FROM plugin AS placeholder, plugin AS kept
    WHERE file.plugin_id = placeholder.id
      AND placeholder.key = 'Amazon'
      AND kept.key = 'Amazon Prime Video'
      AND NOT EXISTS (
          SELECT 1
          FROM file AS existing
          WHERE existing.plugin_id = kept.id
            AND existing.key = file.key
      )
"""

_DROP_PLACEHOLDER_PLUGIN = """
    DELETE FROM plugin AS placeholder
    WHERE placeholder.key = 'Amazon'
      AND EXISTS (
          SELECT 1 FROM plugin AS kept WHERE kept.key = 'Amazon Prime Video'
      )
"""

_RENAME_PLUGIN = """
    UPDATE plugin SET key = 'Amazon' WHERE key = 'Amazon Prime Video'
"""

_RESTORE_PLUGIN = """
    UPDATE plugin SET key = 'Amazon Prime Video' WHERE key = 'Amazon'
"""

_RESTORE_SOURCE = """
    UPDATE source
    SET key = 'Amazon Prime Video'
    FROM plugin
    WHERE plugin.id = source.plugin_id
      AND plugin.key = 'Amazon Prime Video'
      AND source.key = 'Amazon'
"""

_RENAME_UNMATCHED_TITLES = """
    UPDATE unmatchedtitle
    SET plugin_key = 'Amazon'
    WHERE plugin_key = 'Amazon Prime Video'
"""

_RESTORE_UNMATCHED_TITLES = """
    UPDATE unmatchedtitle
    SET plugin_key = 'Amazon Prime Video'
    WHERE plugin_key = 'Amazon'
"""

_RENAME_CHANNELS = """
    UPDATE channel
    SET name = replace(name, ' on Amazon Prime Video', ' on Amazon'),
        description = replace(
            description,
            ' on Amazon Prime Video.',
            ' on Amazon.'
        )
    WHERE name LIKE '% on Amazon Prime Video'
       OR description LIKE '% on Amazon Prime Video.%'
"""

_RESTORE_CHANNELS = """
    UPDATE channel
    SET name = replace(name, ' on Amazon', ' on Amazon Prime Video'),
        description = replace(
            description,
            ' on Amazon.',
            ' on Amazon Prime Video.'
        )
    WHERE name LIKE '% on Amazon'
       OR description LIKE '% on Amazon.%'
"""


# TODO: Validate
def upgrade() -> None:
    op.execute(_RENAME_SOURCE)
    op.execute(_ADOPT_SOURCES)
    op.execute(_ADOPT_FILES)
    op.execute(_DROP_PLACEHOLDER_PLUGIN)
    op.execute(_RENAME_PLUGIN)
    op.execute(_RENAME_UNMATCHED_TITLES)
    op.execute(_RENAME_CHANNELS)


# TODO: Validate
def downgrade() -> None:
    op.execute(_RESTORE_CHANNELS)
    op.execute(_RESTORE_UNMATCHED_TITLES)
    op.execute(_RESTORE_PLUGIN)
    op.execute(_RESTORE_SOURCE)
