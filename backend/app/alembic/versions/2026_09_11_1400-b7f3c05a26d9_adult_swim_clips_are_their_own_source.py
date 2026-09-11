# TODO: Validate
"""Adult Swim clips are carried by a source of their own, off TMDB."""

from alembic import op

revision = "b7f3c05a26d9"
down_revision = "e5b27a91c4d8"
branch_labels = None
depends_on = None


_ADD_CLIPS_SOURCE = """
    INSERT INTO source (
        id,
        created_at,
        modified_at,
        key,
        extra,
        link_to_tmdb,
        favicon_url,
        data_timestamp,
        plugin_id
    )
    SELECT gen_random_uuid(),
           now(),
           now(),
           'Adult Swim Clips',
           '{}'::jsonb,
           false,
           source.favicon_url,
           source.data_timestamp,
           source.plugin_id
    FROM source
    JOIN plugin ON plugin.id = source.plugin_id
    WHERE plugin.key = 'Adult Swim'
      AND source.key = 'Adult Swim Free'
      AND NOT EXISTS (
          SELECT 1
          FROM source AS clips
          WHERE clips.plugin_id = source.plugin_id
            AND clips.key = 'Adult Swim Clips'
      )
"""

_DROP_CLIPS_SOURCE = """
    DELETE FROM source
    USING plugin
    WHERE plugin.id = source.plugin_id
      AND plugin.key = 'Adult Swim'
      AND source.key = 'Adult Swim Clips'
"""


# TODO: Validate
def upgrade() -> None:
    op.execute(_ADD_CLIPS_SOURCE)


# TODO: Validate
def downgrade() -> None:
    op.execute(_DROP_CLIPS_SOURCE)
