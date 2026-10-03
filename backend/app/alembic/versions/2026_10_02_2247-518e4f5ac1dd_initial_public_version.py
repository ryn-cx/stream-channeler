"""Initial public version

Revision ID: 518e4f5ac1dd
Revises: fe56fa70289e
Create Date: 2026-10-02 22:47:21.091382

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql

revision = '518e4f5ac1dd'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


FUNCTIONS = (
    r'''
CREATE OR REPLACE FUNCTION public.episode_linked_flag()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            NEW.is_linked := EXISTS (
                SELECT 1 FROM episodetmdbepisode
                WHERE episodetmdbepisode.episode_id = NEW.id
            );
            RETURN NEW;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.episode_tmdb_title()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            PERFORM refresh_episode_tmdb_title(
                ARRAY(
                    SELECT NEW.id
                    UNION
                    SELECT link.episode_id
                    FROM episodetmdbepisode link
                    WHERE link.tmdb_episode_id = NEW.id
                )
            );
            RETURN NULL;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.episodetmdbepisode_linked_flag()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                UPDATE episode SET is_linked = is_linked
                WHERE id = OLD.episode_id;
            END IF;
            IF TG_OP <> 'DELETE' THEN
                UPDATE episode SET is_linked = is_linked
                WHERE id = NEW.episode_id;
            END IF;
            RETURN NULL;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.episodetmdbepisode_tmdb_title()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM refresh_episode_tmdb_title(ARRAY[OLD.episode_id]);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM refresh_episode_tmdb_title(ARRAY[NEW.episode_id]);
            END IF;
            RETURN NULL;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.refresh_episode_tmdb_title(episode_ids uuid[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
        BEGIN
            DELETE FROM episodetmdbtitle
            WHERE episodetmdbtitle.episode_id = ANY(episode_ids);

            INSERT INTO episodetmdbtitle (episode_id, tmdb_title_id)
            SELECT resolved.episode_id, resolved.tmdb_title_id
            FROM (

        SELECT DISTINCT
            episode.id AS episode_id,
            COALESCE(
                tmdb_season.title_id,
                titletmdbtitle.tmdb_title_id,
                CASE WHEN NOT title.is_linked THEN title.id END
            ) AS tmdb_title_id
        FROM episode
        JOIN season ON season.id = episode.season_id
        JOIN title ON title.id = season.title_id
        LEFT JOIN episodetmdbepisode link
            ON link.episode_id = episode.id
        LEFT JOIN episode tmdb_episode
            ON tmdb_episode.id = link.tmdb_episode_id
            AND NOT tmdb_episode.is_linked
        LEFT JOIN season tmdb_season
            ON tmdb_season.id = tmdb_episode.season_id
        LEFT JOIN titletmdbtitle
            ON titletmdbtitle.title_id = title.id
            AND NOT episode.is_linked
     WHERE episode.id = ANY(episode_ids)
            ) AS resolved
            WHERE resolved.tmdb_title_id IS NOT NULL
            ON CONFLICT DO NOTHING;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.refresh_episode_tmdb_title_of_title(target_title uuid)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
        BEGIN
            PERFORM refresh_episode_tmdb_title(
                ARRAY(
                    SELECT episode.id
                    FROM episode
                    JOIN season ON season.id = episode.season_id
                    WHERE season.title_id = target_title
                )
            );
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.season_tmdb_title()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            PERFORM refresh_episode_tmdb_title(
                ARRAY(
                    SELECT episode.id FROM episode WHERE episode.season_id = NEW.id
                    UNION
                    SELECT link.episode_id
                    FROM episodetmdbepisode link
                    JOIN episode ON episode.id = link.tmdb_episode_id
                    WHERE episode.season_id = NEW.id
                )
            );
            RETURN NULL;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.title_linked_flag()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            NEW.is_linked := EXISTS (
                SELECT 1 FROM titletmdbtitle
                WHERE titletmdbtitle.title_id = NEW.id
            );
            RETURN NEW;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.title_tmdb_title()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            PERFORM refresh_episode_tmdb_title_of_title(NEW.id);
            RETURN NULL;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.titletmdbtitle_linked_flag()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                UPDATE title SET is_linked = is_linked
                WHERE id = OLD.title_id;
            END IF;
            IF TG_OP <> 'DELETE' THEN
                UPDATE title SET is_linked = is_linked
                WHERE id = NEW.title_id;
            END IF;
            RETURN NULL;
        END;
        $function$
''',
    r'''
CREATE OR REPLACE FUNCTION public.titletmdbtitle_tmdb_title()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                PERFORM refresh_episode_tmdb_title_of_title(OLD.title_id);
            END IF;
            IF TG_OP <> 'DELETE' THEN
                PERFORM refresh_episode_tmdb_title_of_title(NEW.title_id);
            END IF;
            RETURN NULL;
        END;
        $function$
''',
)

TRIGGERS = (
    r'''
CREATE TRIGGER "Episode-linked-flag" BEFORE INSERT OR UPDATE OF is_linked ON public.episode FOR EACH ROW EXECUTE FUNCTION episode_linked_flag()
''',
    r'''
CREATE TRIGGER "Episode-tmdb-title" AFTER INSERT OR UPDATE OF season_id, is_linked ON public.episode FOR EACH ROW EXECUTE FUNCTION episode_tmdb_title()
''',
    r'''
CREATE TRIGGER "EpisodeTmdbEpisode-linked-flag" AFTER INSERT OR DELETE OR UPDATE ON public.episodetmdbepisode FOR EACH ROW EXECUTE FUNCTION episodetmdbepisode_linked_flag()
''',
    r'''
CREATE TRIGGER "EpisodeTmdbEpisode-tmdb-title" AFTER INSERT OR DELETE OR UPDATE ON public.episodetmdbepisode FOR EACH ROW EXECUTE FUNCTION episodetmdbepisode_tmdb_title()
''',
    r'''
CREATE TRIGGER "Season-tmdb-title" AFTER UPDATE OF title_id ON public.season FOR EACH ROW EXECUTE FUNCTION season_tmdb_title()
''',
    r'''
CREATE TRIGGER "Title-linked-flag" BEFORE INSERT OR UPDATE OF is_linked ON public.title FOR EACH ROW EXECUTE FUNCTION title_linked_flag()
''',
    r'''
CREATE TRIGGER "Title-tmdb-title" AFTER UPDATE OF is_linked ON public.title FOR EACH ROW EXECUTE FUNCTION title_tmdb_title()
''',
    r'''
CREATE TRIGGER "TitleTmdbTitle-linked-flag" AFTER INSERT OR DELETE OR UPDATE ON public.titletmdbtitle FOR EACH ROW EXECUTE FUNCTION titletmdbtitle_linked_flag()
''',
    r'''
CREATE TRIGGER "TitleTmdbTitle-tmdb-title" AFTER INSERT OR DELETE OR UPDATE ON public.titletmdbtitle FOR EACH ROW EXECUTE FUNCTION titletmdbtitle_tmdb_title()
''',
)

TRIGRAM_INDEX = r'''
CREATE INDEX "Episode-canonical-name-trigram-index" ON public.episode USING gist (name gist_trgm_ops) WHERE ((is_linked IS FALSE) AND (name IS NOT NULL))
'''

FUNCTION_SIGNATURES = (
    'episode_linked_flag()',
    'episode_tmdb_title()',
    'episodetmdbepisode_linked_flag()',
    'episodetmdbepisode_tmdb_title()',
    'refresh_episode_tmdb_title(episode_ids uuid[])',
    'refresh_episode_tmdb_title_of_title(target_title uuid)',
    'season_tmdb_title()',
    'title_linked_flag()',
    'title_tmdb_title()',
    'titletmdbtitle_linked_flag()',
    'titletmdbtitle_tmdb_title()',
)


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.create_table('plugin',
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('data_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('update_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('upserted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('version', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('hidden', sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.PrimaryKeyConstraint('key'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('Plugin-deleted_at-index', 'plugin', ['deleted_at'], unique=False)
    op.create_table('watchprovider',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tmdb_provider_id', sa.Integer(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('logo_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('tmdb_provider_id', name='WatchProvider-tmdb_provider_id-unique')
    )
    op.create_table('channel',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('channel_number', sa.Float(), nullable=True),
    sa.Column('visibility', sa.Enum('public', 'unlisted', 'private', name='visibility'), nullable=False),
    sa.Column('default_order', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('anonymous', sa.Boolean(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('update_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_tag_based', sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column('data_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('Channel-user_id-index', 'channel', ['user_id'], unique=False)
    op.create_table('channelorder',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('config', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('visibility', sa.Enum('public', 'unlisted', 'private', name='visibility'), nullable=False),
    sa.Column('anonymous', sa.Boolean(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('icon', sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelOrder-user_id-index', 'channelorder', ['user_id'], unique=False)
    op.create_table('file',
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('data_timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('update_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('upserted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('plugin_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['plugin_id'], ['plugin.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('plugin_id', 'key'),
    sa.UniqueConstraint('id')
    )
    op.create_table('source',
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('data_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('update_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('upserted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('link_to_tmdb', sa.Boolean(), nullable=False),
    sa.Column('favicon_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('plugin_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['plugin_id'], ['plugin.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('plugin_id', 'key'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('Source-deleted_at-index', 'source', ['deleted_at'], unique=False)
    op.create_index('Source-key-index', 'source', ['key'], unique=False, postgresql_where=None)
    op.create_table('useraction',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('ip_address', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('action', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('UserAction-action-created_at-index', 'useraction', ['action', 'created_at'], unique=False)
    op.create_index('UserAction-ip_address-created_at-index', 'useraction', ['ip_address', 'created_at'], unique=False)
    op.create_index('UserAction-user_id-created_at-index', 'useraction', ['user_id', 'created_at'], unique=False)
    op.create_table('usersourcepreference',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('source_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'source_key'),
    sa.UniqueConstraint('id')
    )
    op.create_table('channelcombinedchannel',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('channel_id', sa.Uuid(), nullable=False),
    sa.Column('combined_channel_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['combined_channel_id'], ['channel.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_id', 'combined_channel_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelCombinedChannel-combined_channel_id-index', 'channelcombinedchannel', ['combined_channel_id'], unique=False)
    op.create_table('channelfavorite',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('channel_id', sa.Uuid(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('channel_number', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'channel_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelFavorite-channel_id-index', 'channelfavorite', ['channel_id'], unique=False)
    op.create_table('channelorderfavorite',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('channel_order_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_order_id'], ['channelorder.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'channel_order_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelOrderFavorite-channel_order_id-index', 'channelorderfavorite', ['channel_order_id'], unique=False)
    op.create_table('channelqueue',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'FAILED', 'IMPORTED', 'IMPORTING', name='urlstatus'), nullable=False),
    sa.Column('note', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('import_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('channel_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_id', 'url'),
    sa.UniqueConstraint('id')
    )
    op.create_table('comment',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('body', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('channel_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('parent_comment_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['parent_comment_id'], ['comment.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('Comment-channel_id-index', 'comment', ['channel_id'], unique=False)
    op.create_index('Comment-parent_comment_id-index', 'comment', ['parent_comment_id'], unique=False)
    op.create_index('Comment-user_id-index', 'comment', ['user_id'], unique=False)
    op.create_table('title',
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('data_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('update_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('upserted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('media_type', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('poster_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('poster_thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('tmdb_score', sa.Float(), nullable=True),
    sa.Column('tmdb_popularity', sa.Float(), nullable=True),
    sa.Column('original_language', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('tmdb_title_validated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tmdb_absent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('imdb_score', sa.Float(), nullable=True),
    sa.Column('imdb_popularity', sa.Integer(), nullable=True),
    sa.Column('link_status', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('is_linked', sa.Boolean(), nullable=False),
    sa.Column('source_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['source.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('source_id', 'key'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('Title-deleted_at-index', 'title', ['deleted_at'], unique=False)
    op.create_index('Title-is_linked-index', 'title', ['is_linked'], unique=False)
    op.create_index('Title-link_status-index', 'title', ['link_status'], unique=False, postgresql_where=sa.text('link_status IS NULL'))
    op.create_index('Title-media_type-index', 'title', ['media_type'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_index('Title-name-index', 'title', ['name'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_index('Title-unlinked-key-index', 'title', ['key'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_table('commentnotification',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('comment_id', sa.Uuid(), nullable=False),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['comment_id'], ['comment.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'comment_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('CommentNotification-comment_id-index', 'commentnotification', ['comment_id'], unique=False)
    op.create_table('season',
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('data_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('update_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('upserted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('season_number', sa.Integer(), nullable=True),
    sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=True),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('title_id', 'key'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('Season-deleted_at-index', 'season', ['deleted_at'], unique=False)
    op.create_index('Season-name-index', 'season', ['name'], unique=False, postgresql_where=None)
    op.create_index('Season-season_number-index', 'season', ['season_number'], unique=False, postgresql_where=None)
    op.create_index('Season-sort_order-index', 'season', ['sort_order'], unique=False, postgresql_where=None)
    op.create_table('titlegenre',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('title_id', 'name'),
    sa.UniqueConstraint('id')
    )
    op.create_index('TitleGenre-name-index', 'titlegenre', ['name'], unique=False)
    op.create_table('titleissuereport',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('report', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('TitleIssueReport-title_id-index', 'titleissuereport', ['title_id'], unique=False)
    op.create_index('TitleIssueReport-user_id-index', 'titleissuereport', ['user_id'], unique=False)
    op.create_table('titlespokenlanguage',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('title_id', 'code'),
    sa.UniqueConstraint('id')
    )
    op.create_index('TitleSpokenLanguage-code-index', 'titlespokenlanguage', ['code'], unique=False)
    op.create_table('titletmdbtitle',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.Column('tmdb_title_id', sa.Uuid(), nullable=False),
    sa.Column('note', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('manual_tmdb_link', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('title_id', 'tmdb_title_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('TitleTmdbTitle-tmdb_title_id-index', 'titletmdbtitle', ['tmdb_title_id'], unique=False)
    op.create_table('titlewatchprovider',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.Column('watch_provider_id', sa.Uuid(), nullable=False),
    sa.Column('region', sqlmodel.sql.sqltypes.AutoString(length=2), nullable=False),
    sa.Column('offering_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['watch_provider_id'], ['watchprovider.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('title_id', 'region', 'watch_provider_id', 'offering_type'),
    sa.UniqueConstraint('id')
    )
    op.create_index('TitleWatchProvider-region-watch_provider_id-index', 'titlewatchprovider', ['region', 'watch_provider_id'], unique=False)
    op.create_table('tmdbepisodeorder',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tmdb_group_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('type', sa.Integer(), nullable=True),
    sa.Column('group_count', sa.Integer(), nullable=True),
    sa.Column('episode_count', sa.Integer(), nullable=True),
    sa.Column('tmdb_title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['tmdb_title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('tmdb_title_id', 'tmdb_group_id'),
    sa.UniqueConstraint('id')
    )
    op.create_table('unmatchedtitle',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('provider_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('plugin_key', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('ignored_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('title_id', 'provider_name', name='UnmatchedTitle-title_id-provider_name-unique')
    )
    op.create_index('UnmatchedTitle-title_id-index', 'unmatchedtitle', ['title_id'], unique=False)
    op.create_table('channeltitle',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('channel_id', sa.Uuid(), nullable=False),
    sa.Column('tmdb_title_id', sa.Uuid(), nullable=False),
    sa.Column('is_whitelist', sa.Boolean(), nullable=False),
    sa.Column('is_blacklist_only', sa.Boolean(), nullable=False),
    sa.Column('imported_title_id', sa.Uuid(), nullable=False),
    sa.Column('tmdb_episode_order_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['imported_title_id'], ['title.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_episode_order_id'], ['tmdbepisodeorder.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tmdb_title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_id', 'tmdb_title_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelTitle-imported_title_id-index', 'channeltitle', ['imported_title_id'], unique=False)
    op.create_index('ChannelTitle-titled_channel_id-index', 'channeltitle', ['channel_id'], unique=False, postgresql_where=sa.text('is_blacklist_only IS FALSE'))
    op.create_index('ChannelTitle-tmdb_title_id-index', 'channeltitle', ['tmdb_title_id'], unique=False)
    op.create_table('episode',
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('data_timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.Column('update_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('extra', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('upserted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('image_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('air_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('episode_number', sa.Integer(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=True),
    sa.Column('tmdb_episode_validated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tmdb_absent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('tmdb_note', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('ignored_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_linked', sa.Boolean(), nullable=False),
    sa.Column('watch_identifier', sa.Text(), nullable=False),
    sa.Column('season_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['season_id'], ['season.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('season_id', 'key'),
    sa.UniqueConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('Episode-air_date-index', 'episode', ['air_date'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_index('Episode-deleted_at-index', 'episode', ['deleted_at'], unique=False)
    op.create_index('Episode-duration-index', 'episode', ['duration'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_index('Episode-episode_number-index', 'episode', ['episode_number'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_index('Episode-ignored_at-index', 'episode', ['ignored_at'], unique=False, postgresql_where=sa.text('ignored_at IS NOT NULL'))
    op.create_index('Episode-is_linked-index', 'episode', ['is_linked'], unique=False)
    op.create_index('Episode-name-index', 'episode', ['name'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_index('Episode-sort_order-index', 'episode', ['sort_order'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_index('Episode-unlinked-key-index', 'episode', ['key'], unique=False, postgresql_where=sa.text('is_linked IS FALSE'))
    op.create_index('Episode-watch_identifier-index', 'episode', ['watch_identifier'], unique=False)
    op.create_table('seasonissuereport',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('report', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('season_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['season_id'], ['season.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('SeasonIssueReport-season_id-index', 'seasonissuereport', ['season_id'], unique=False)
    op.create_index('SeasonIssueReport-user_id-index', 'seasonissuereport', ['user_id'], unique=False)
    op.create_table('tmdbepisodeordergroup',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('group_index', sa.Integer(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['tmdbepisodeorder.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('order_id', 'group_index'),
    sa.UniqueConstraint('id')
    )
    op.create_table('channelepisodefilter',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tmdb_episode_id', sa.Uuid(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('channel_title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_title_id'], ['channeltitle.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_title_id', 'tmdb_episode_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelEpisodeFilter-tmdb_episode_id-index', 'channelepisodefilter', ['tmdb_episode_id'], unique=False)
    op.create_table('channelepisodesourcefilter',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tmdb_episode_id', sa.Uuid(), nullable=False),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('channel_title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_title_id'], ['channeltitle.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_title_id', 'tmdb_episode_id', 'title_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelEpisodeSourceFilter-title_id-index', 'channelepisodesourcefilter', ['title_id'], unique=False)
    op.create_index('ChannelEpisodeSourceFilter-tmdb_episode_id-index', 'channelepisodesourcefilter', ['tmdb_episode_id'], unique=False)
    op.create_table('channelordergroupfilter',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tmdb_episode_order_group_id', sa.Uuid(), nullable=False),
    sa.Column('channel_title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_title_id'], ['channeltitle.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_episode_order_group_id'], ['tmdbepisodeordergroup.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_title_id', 'tmdb_episode_order_group_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelOrderGroupFilter-tmdb_episode_order_group_id-index', 'channelordergroupfilter', ['tmdb_episode_order_group_id'], unique=False)
    op.create_table('channelsavedepisodeorder',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.Uuid(), nullable=False),
    sa.Column('tmdb_episode_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['channel.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_id', 'tmdb_episode_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelSavedEpisodeOrder-channel_id-position-index', 'channelsavedepisodeorder', ['channel_id', 'position'], unique=False)
    op.create_index('ChannelSavedEpisodeOrder-tmdb_episode_id-index', 'channelsavedepisodeorder', ['tmdb_episode_id'], unique=False)
    op.create_table('channelseasonfilter',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('season_id', sa.Uuid(), nullable=False),
    sa.Column('channel_title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_title_id'], ['channeltitle.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['season_id'], ['season.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_title_id', 'season_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelSeasonFilter-season_id-index', 'channelseasonfilter', ['season_id'], unique=False)
    op.create_table('channelsourcefilter',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('title_id', sa.Uuid(), nullable=False),
    sa.Column('channel_title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['channel_title_id'], ['channeltitle.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('channel_title_id', 'title_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('ChannelSourceFilter-title_id-index', 'channelsourcefilter', ['title_id'], unique=False)
    op.create_table('episodeissuereport',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('report', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('episode_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('EpisodeIssueReport-episode_id-index', 'episodeissuereport', ['episode_id'], unique=False)
    op.create_index('EpisodeIssueReport-user_id-index', 'episodeissuereport', ['user_id'], unique=False)
    op.create_table('episodetmdbepisode',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('episode_id', sa.Uuid(), nullable=False),
    sa.Column('tmdb_episode_id', sa.Uuid(), nullable=False),
    sa.Column('note', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('manual_tmdb_link', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('episode_id', 'tmdb_episode_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('EpisodeTmdbEpisode-tmdb_episode_id-index', 'episodetmdbepisode', ['tmdb_episode_id'], unique=False)
    op.create_table('episodetmdbtitle',
    sa.Column('episode_id', sa.Uuid(), nullable=False),
    sa.Column('tmdb_title_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_title_id'], ['title.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('episode_id', 'tmdb_title_id')
    )
    op.create_index('EpisodeTmdbTitle-tmdb_title_id-index', 'episodetmdbtitle', ['tmdb_title_id', 'episode_id'], unique=False)
    op.create_table('tmdbepisodeorderentry',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('episode_number', sa.Integer(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Uuid(), nullable=False),
    sa.Column('group_id', sa.Uuid(), nullable=False),
    sa.Column('tmdb_episode_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['tmdbepisodeordergroup.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['order_id'], ['tmdbepisodeorder.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tmdb_episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('order_id', 'tmdb_episode_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('TmdbEpisodeOrderEntry-group_id-sort_order-index', 'tmdbepisodeorderentry', ['group_id', 'sort_order'], unique=False)
    op.create_index('TmdbEpisodeOrderEntry-tmdb_episode_id-index', 'tmdbepisodeorderentry', ['tmdb_episode_id'], unique=False)
    op.create_table('userepisodeurl',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('tmdb_episode_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['tmdb_episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', 'tmdb_episode_id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('UserEpisodeUrl-tmdb_episode_id-index', 'userepisodeurl', ['tmdb_episode_id'], unique=False)
    op.create_table('watch',
    sa.Column('watch_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('watch_identifier', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('episode_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['episode_id'], ['episode.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.create_index('Watch-episode_id-index', 'watch', ['episode_id'], unique=False)
    op.create_index('Watch-user_id-completed-index', 'watch', ['user_id', 'completed'], unique=False)
    op.create_index('Watch-user_id-episode_id-index', 'watch', ['user_id', 'episode_id'], unique=False)
    op.create_index('Watch-user_id-watch_identifier-watch_date-key', 'watch', ['user_id', 'watch_identifier', 'watch_date'], unique=True)
    op.create_index('Watch-watch_date-index', 'watch', ['watch_date'], unique=False)
    op.create_index('Watch-watch_identifier-index', 'watch', ['watch_identifier'], unique=False)
    op.drop_table('item')
    op.add_column('user', sa.Column('username', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False))
    op.add_column('user', sa.Column('server_side_threshold', sa.Integer(), nullable=False))
    op.create_index('ix_user_username_lower', 'user', [sa.literal_column('lower(username)')], unique=True)
    op.drop_column('user', 'full_name')
    for function in FUNCTIONS:
        op.execute(function)
    for trigger in TRIGGERS:
        op.execute(trigger)
    op.execute(TRIGRAM_INDEX)


def downgrade():
    op.execute('DROP INDEX "Episode-canonical-name-trigram-index"')
    op.add_column('user', sa.Column('full_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.drop_index('ix_user_username_lower', table_name='user')
    op.drop_column('user', 'server_side_threshold')
    op.drop_column('user', 'username')
    op.create_table('item',
    sa.Column('description', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    sa.Column('title', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('owner_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['user.id'], name=op.f('item_owner_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('item_pkey'))
    )
    op.drop_index('Watch-watch_identifier-index', table_name='watch')
    op.drop_index('Watch-watch_date-index', table_name='watch')
    op.drop_index('Watch-user_id-watch_identifier-watch_date-key', table_name='watch')
    op.drop_index('Watch-user_id-episode_id-index', table_name='watch')
    op.drop_index('Watch-user_id-completed-index', table_name='watch')
    op.drop_index('Watch-episode_id-index', table_name='watch')
    op.drop_table('watch')
    op.drop_index('UserEpisodeUrl-tmdb_episode_id-index', table_name='userepisodeurl')
    op.drop_table('userepisodeurl')
    op.drop_index('TmdbEpisodeOrderEntry-tmdb_episode_id-index', table_name='tmdbepisodeorderentry')
    op.drop_index('TmdbEpisodeOrderEntry-group_id-sort_order-index', table_name='tmdbepisodeorderentry')
    op.drop_table('tmdbepisodeorderentry')
    op.drop_index('EpisodeTmdbTitle-tmdb_title_id-index', table_name='episodetmdbtitle')
    op.drop_table('episodetmdbtitle')
    op.drop_index('EpisodeTmdbEpisode-tmdb_episode_id-index', table_name='episodetmdbepisode')
    op.drop_table('episodetmdbepisode')
    op.drop_index('EpisodeIssueReport-user_id-index', table_name='episodeissuereport')
    op.drop_index('EpisodeIssueReport-episode_id-index', table_name='episodeissuereport')
    op.drop_table('episodeissuereport')
    op.drop_index('ChannelSourceFilter-title_id-index', table_name='channelsourcefilter')
    op.drop_table('channelsourcefilter')
    op.drop_index('ChannelSeasonFilter-season_id-index', table_name='channelseasonfilter')
    op.drop_table('channelseasonfilter')
    op.drop_index('ChannelSavedEpisodeOrder-tmdb_episode_id-index', table_name='channelsavedepisodeorder')
    op.drop_index('ChannelSavedEpisodeOrder-channel_id-position-index', table_name='channelsavedepisodeorder')
    op.drop_table('channelsavedepisodeorder')
    op.drop_index('ChannelOrderGroupFilter-tmdb_episode_order_group_id-index', table_name='channelordergroupfilter')
    op.drop_table('channelordergroupfilter')
    op.drop_index('ChannelEpisodeSourceFilter-tmdb_episode_id-index', table_name='channelepisodesourcefilter')
    op.drop_index('ChannelEpisodeSourceFilter-title_id-index', table_name='channelepisodesourcefilter')
    op.drop_table('channelepisodesourcefilter')
    op.drop_index('ChannelEpisodeFilter-tmdb_episode_id-index', table_name='channelepisodefilter')
    op.drop_table('channelepisodefilter')
    op.drop_table('tmdbepisodeordergroup')
    op.drop_index('SeasonIssueReport-user_id-index', table_name='seasonissuereport')
    op.drop_index('SeasonIssueReport-season_id-index', table_name='seasonissuereport')
    op.drop_table('seasonissuereport')
    op.drop_index('Episode-watch_identifier-index', table_name='episode')
    op.drop_index('Episode-unlinked-key-index', table_name='episode', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_index('Episode-sort_order-index', table_name='episode', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_index('Episode-name-index', table_name='episode', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_index('Episode-is_linked-index', table_name='episode')
    op.drop_index('Episode-ignored_at-index', table_name='episode', postgresql_where=sa.text('ignored_at IS NOT NULL'))
    op.drop_index('Episode-episode_number-index', table_name='episode', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_index('Episode-duration-index', table_name='episode', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_index('Episode-deleted_at-index', table_name='episode')
    op.drop_index('Episode-air_date-index', table_name='episode', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_table('episode')
    op.drop_index('ChannelTitle-tmdb_title_id-index', table_name='channeltitle')
    op.drop_index('ChannelTitle-titled_channel_id-index', table_name='channeltitle', postgresql_where=sa.text('is_blacklist_only IS FALSE'))
    op.drop_index('ChannelTitle-imported_title_id-index', table_name='channeltitle')
    op.drop_table('channeltitle')
    op.drop_index('UnmatchedTitle-title_id-index', table_name='unmatchedtitle')
    op.drop_table('unmatchedtitle')
    op.drop_table('tmdbepisodeorder')
    op.drop_index('TitleWatchProvider-region-watch_provider_id-index', table_name='titlewatchprovider')
    op.drop_table('titlewatchprovider')
    op.drop_index('TitleTmdbTitle-tmdb_title_id-index', table_name='titletmdbtitle')
    op.drop_table('titletmdbtitle')
    op.drop_index('TitleSpokenLanguage-code-index', table_name='titlespokenlanguage')
    op.drop_table('titlespokenlanguage')
    op.drop_index('TitleIssueReport-user_id-index', table_name='titleissuereport')
    op.drop_index('TitleIssueReport-title_id-index', table_name='titleissuereport')
    op.drop_table('titleissuereport')
    op.drop_index('TitleGenre-name-index', table_name='titlegenre')
    op.drop_table('titlegenre')
    op.drop_index('Season-sort_order-index', table_name='season', postgresql_where=None)
    op.drop_index('Season-season_number-index', table_name='season', postgresql_where=None)
    op.drop_index('Season-name-index', table_name='season', postgresql_where=None)
    op.drop_index('Season-deleted_at-index', table_name='season')
    op.drop_table('season')
    op.drop_index('CommentNotification-comment_id-index', table_name='commentnotification')
    op.drop_table('commentnotification')
    op.drop_index('Title-unlinked-key-index', table_name='title', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_index('Title-name-index', table_name='title', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_index('Title-media_type-index', table_name='title', postgresql_where=sa.text('is_linked IS FALSE'))
    op.drop_index('Title-link_status-index', table_name='title', postgresql_where=sa.text('link_status IS NULL'))
    op.drop_index('Title-is_linked-index', table_name='title')
    op.drop_index('Title-deleted_at-index', table_name='title')
    op.drop_table('title')
    op.drop_index('Comment-user_id-index', table_name='comment')
    op.drop_index('Comment-parent_comment_id-index', table_name='comment')
    op.drop_index('Comment-channel_id-index', table_name='comment')
    op.drop_table('comment')
    op.drop_table('channelqueue')
    op.drop_index('ChannelOrderFavorite-channel_order_id-index', table_name='channelorderfavorite')
    op.drop_table('channelorderfavorite')
    op.drop_index('ChannelFavorite-channel_id-index', table_name='channelfavorite')
    op.drop_table('channelfavorite')
    op.drop_index('ChannelCombinedChannel-combined_channel_id-index', table_name='channelcombinedchannel')
    op.drop_table('channelcombinedchannel')
    op.drop_table('usersourcepreference')
    op.drop_index('UserAction-user_id-created_at-index', table_name='useraction')
    op.drop_index('UserAction-ip_address-created_at-index', table_name='useraction')
    op.drop_index('UserAction-action-created_at-index', table_name='useraction')
    op.drop_table('useraction')
    op.drop_index('Source-key-index', table_name='source', postgresql_where=None)
    op.drop_index('Source-deleted_at-index', table_name='source')
    op.drop_table('source')
    op.drop_table('file')
    op.drop_index('ChannelOrder-user_id-index', table_name='channelorder')
    op.drop_table('channelorder')
    op.drop_index('Channel-user_id-index', table_name='channel')
    op.drop_table('channel')
    op.drop_table('watchprovider')
    op.drop_index('Plugin-deleted_at-index', table_name='plugin')
    op.drop_table('plugin')
    for signature in FUNCTION_SIGNATURES:
        op.execute(f'DROP FUNCTION {signature}')
    op.execute('DROP TYPE urlstatus')
    op.execute('DROP TYPE visibility')
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')
