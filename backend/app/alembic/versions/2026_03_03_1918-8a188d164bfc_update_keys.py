"""Update keys

Revision ID: 8a188d164bfc
Revises: b2f4a1c3d5e6
Create Date: 2026-03-03 19:18:58.171122

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '8a188d164bfc'
down_revision = 'b2f4a1c3d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # All tables use composite PKs with _id_key unique constraints on "id".
    # Most _id_key constraints have FK dependencies and CANNOT be dropped:
    #   episode_id_key  <- channelepisodewhitelist, episodewatch
    #   season_id_key   <- channelseasonwhitelist, episode
    #   show_id_key     <- channelshow, season
    #   source_id_key   <- show
    # Only file_id_key has no FK dependencies.

    # --- Plugin PK: key -> id ---
    op.drop_constraint('file_plugin_id_fkey', 'file', type_='foreignkey')
    op.drop_constraint('source_plugin_id_fkey', 'source', type_='foreignkey')
    op.drop_constraint('plugin_pkey', 'plugin', type_='primary')
    op.drop_constraint('plugin_id_key', 'plugin', type_='unique')
    op.create_primary_key('plugin_pkey', 'plugin', ['id'])
    op.create_unique_constraint('uq_plugin_user_id_key', 'plugin', ['user_id', 'key'], postgresql_nulls_not_distinct=True)
    op.create_foreign_key('file_plugin_id_fkey', 'file', 'plugin', ['plugin_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('source_plugin_id_fkey', 'source', 'plugin', ['plugin_id'], ['id'], ondelete='CASCADE')

    # --- Add CASCADE to plugin -> user FK ---
    op.drop_constraint('plugin_user_id_fkey', 'plugin', type_='foreignkey')
    op.create_foreign_key('plugin_user_id_fkey', 'plugin', 'user', ['user_id'], ['id'], ondelete='CASCADE')

    # --- Drop file_id_key (only one with no FK dependencies) ---
    op.drop_constraint('file_id_key', 'file', type_='unique')


def downgrade():
    op.create_unique_constraint('file_id_key', 'file', ['id'])

    # --- Restore plugin -> user FK ---
    op.drop_constraint('plugin_user_id_fkey', 'plugin', type_='foreignkey')
    op.create_foreign_key('plugin_user_id_fkey', 'plugin', 'user', ['user_id'], ['id'], ondelete='SET NULL')

    # --- Plugin PK: id -> key ---
    op.drop_constraint('file_plugin_id_fkey', 'file', type_='foreignkey')
    op.drop_constraint('source_plugin_id_fkey', 'source', type_='foreignkey')
    op.drop_constraint('uq_plugin_user_id_key', 'plugin', type_='unique')
    op.drop_constraint('plugin_pkey', 'plugin', type_='primary')
    op.create_primary_key('plugin_pkey', 'plugin', ['key'])
    op.create_unique_constraint('plugin_id_key', 'plugin', ['id'])
    op.create_foreign_key('file_plugin_id_fkey', 'file', 'plugin', ['plugin_id'], ['id'])
    op.create_foreign_key('source_plugin_id_fkey', 'source', 'plugin', ['plugin_id'], ['id'])
