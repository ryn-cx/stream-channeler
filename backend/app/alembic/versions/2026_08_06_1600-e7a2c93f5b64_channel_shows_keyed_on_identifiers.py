"""key channel shows and their filters on identifiers

Revision ID: e7a2c93f5b64
Revises: d3b8e6c07a41
Create Date: 2026-08-06 16:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "e7a2c93f5b64"
down_revision = "d3b8e6c07a41"
branch_labels = None
depends_on = None


def upgrade():
    # A channel held one website's copy of a title, so the same title from two
    # websites was two unrelated rows and a filter set on one of them said nothing
    # about the other. A channel now holds the title itself, and which websites'
    # copies of it are wanted is said with `channelsourcefilter` rows.
    op.create_table(
        "channelsourcefilter",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel_show_id", sa.Uuid(), nullable=False),
        sa.Column("show_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["channel_show_id"], ["channelshow.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["show_id"], ["show.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("channel_show_id", "show_id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(
        "ChannelSourceFilter-show_id-index", "channelsourcefilter", ["show_id"]
    )

    op.add_column(
        "channelshow",
        sa.Column("show_identifier", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.execute(
        """
        UPDATE channelshow
        SET show_identifier = show.show_identifier
        FROM show
        WHERE show.id = channelshow.show_id
        """
    )

    op.add_column(
        "channelseasonfilter",
        sa.Column(
            "season_identifier", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.execute(
        """
        UPDATE channelseasonfilter
        SET season_identifier = season.season_identifier
        FROM season
        WHERE season.id = channelseasonfilter.season_id
        """
    )
    op.add_column(
        "channelepisodefilter",
        sa.Column(
            "episode_identifier", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    op.execute(
        """
        UPDATE channelepisodefilter
        SET episode_identifier = episode.episode_identifier
        FROM episode
        WHERE episode.id = channelepisodefilter.episode_id
        """
    )

    # A channel that held two websites' copies of one title now has one row for it.
    # The oldest row is the one kept, since it is the one the rest of the channel was
    # built around, and every filter from the rows being dropped moves onto it.
    op.execute(
        """
        CREATE TEMPORARY TABLE channel_show_merge AS
        SELECT
            channelshow.id AS dropped_id,
            kept.id AS kept_id
        FROM channelshow
        JOIN LATERAL (
            SELECT other.id
            FROM channelshow AS other
            WHERE other.channel_id = channelshow.channel_id
              AND other.show_identifier = channelshow.show_identifier
            ORDER BY other.created_at, other.id
            LIMIT 1
        ) AS kept ON TRUE
        WHERE kept.id <> channelshow.id
        """
    )
    op.execute(
        """
        UPDATE channelseasonfilter
        SET channel_show_id = channel_show_merge.kept_id
        FROM channel_show_merge
        WHERE channel_show_merge.dropped_id = channelseasonfilter.channel_show_id
        """
    )
    op.execute(
        """
        UPDATE channelepisodefilter
        SET channel_show_id = channel_show_merge.kept_id
        FROM channel_show_merge
        WHERE channel_show_merge.dropped_id = channelepisodefilter.channel_show_id
        """
    )
    # A filter that both rows carried is now the same row twice.
    op.execute(
        """
        DELETE FROM channelseasonfilter AS duplicate
        USING channelseasonfilter AS kept
        WHERE duplicate.channel_show_id = kept.channel_show_id
          AND duplicate.season_identifier = kept.season_identifier
          AND duplicate.ctid > kept.ctid
        """
    )
    op.execute(
        """
        DELETE FROM channelepisodefilter AS duplicate
        USING channelepisodefilter AS kept
        WHERE duplicate.channel_show_id = kept.channel_show_id
          AND duplicate.episode_identifier = kept.episode_identifier
          AND duplicate.ctid > kept.ctid
        """
    )
    # A row that was only ever a filter holder stops being one as soon as the row it
    # merges into is a real member of the channel.
    op.execute(
        """
        UPDATE channelshow
        SET is_blacklist_only = FALSE
        FROM channel_show_merge, channelshow AS dropped
        WHERE channel_show_merge.kept_id = channelshow.id
          AND channel_show_merge.dropped_id = dropped.id
          AND dropped.is_blacklist_only = FALSE
        """
    )
    op.execute(
        """
        DELETE FROM channelshow
        USING channel_show_merge
        WHERE channel_show_merge.dropped_id = channelshow.id
        """
    )
    op.execute("DROP TABLE channel_show_merge")

    op.alter_column(
        "channelshow",
        "show_identifier",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )
    op.alter_column(
        "channelseasonfilter",
        "season_identifier",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )
    op.alter_column(
        "channelepisodefilter",
        "episode_identifier",
        existing_type=sqlmodel.sql.sqltypes.AutoString(),
        nullable=False,
    )

    op.drop_constraint("channelshow_pkey", "channelshow", type_="primary")
    op.drop_index("ChannelShow-show_id-index", table_name="channelshow")
    op.drop_column("channelshow", "show_id")
    op.create_primary_key(
        "channelshow_pkey", "channelshow", ["channel_id", "show_identifier"]
    )
    op.create_index(
        "ChannelShow-show_identifier-index", "channelshow", ["show_identifier"]
    )

    # The filter tables were renamed from "whitelist" long after their constraints
    # were named, so the primary keys still carry the old table names.
    op.drop_constraint(
        "channelseasonwhitelist_pkey", "channelseasonfilter", type_="primary"
    )
    op.drop_index("ChannelSeasonFilter-season_id-index", table_name="channelseasonfilter")
    op.drop_column("channelseasonfilter", "season_id")
    op.create_primary_key(
        "channelseasonfilter_pkey",
        "channelseasonfilter",
        ["channel_show_id", "season_identifier"],
    )

    op.drop_constraint(
        "channelepisodewhitelist_pkey", "channelepisodefilter", type_="primary"
    )
    op.drop_index(
        "ChannelEpisodeFilter-episode_id-index", table_name="channelepisodefilter"
    )
    op.drop_column("channelepisodefilter", "episode_id")
    op.create_primary_key(
        "channelepisodefilter_pkey",
        "channelepisodefilter",
        ["channel_show_id", "episode_identifier"],
    )


def downgrade():
    # A merged row cannot be split back into the rows it came from, so each one is
    # pointed back at a single copy of its title: the one the identifier resolves to.
    op.add_column("channelshow", sa.Column("show_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE channelshow
        SET show_id = chosen.id
        FROM (
            SELECT DISTINCT ON (show_identifier) show_identifier, id
            FROM show
            WHERE deleted_at IS NULL
            ORDER BY show_identifier, created_at, id
        ) AS chosen
        WHERE chosen.show_identifier = channelshow.show_identifier
        """
    )
    op.execute("DELETE FROM channelshow WHERE show_id IS NULL")
    op.alter_column("channelshow", "show_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("channelshow_pkey", "channelshow", type_="primary")
    op.drop_index("ChannelShow-show_identifier-index", table_name="channelshow")
    op.drop_column("channelshow", "show_identifier")
    op.create_primary_key("channelshow_pkey", "channelshow", ["channel_id", "show_id"])
    op.create_index("ChannelShow-show_id-index", "channelshow", ["show_id"])
    op.create_foreign_key(
        "channelshow_show_id_fkey",
        "channelshow",
        "show",
        ["show_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column("channelseasonfilter", sa.Column("season_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE channelseasonfilter
        SET season_id = chosen.id
        FROM (
            SELECT DISTINCT ON (season_identifier) season_identifier, id
            FROM season
            WHERE deleted_at IS NULL
            ORDER BY season_identifier, created_at, id
        ) AS chosen
        WHERE chosen.season_identifier = channelseasonfilter.season_identifier
        """
    )
    op.execute("DELETE FROM channelseasonfilter WHERE season_id IS NULL")
    op.alter_column(
        "channelseasonfilter", "season_id", existing_type=sa.Uuid(), nullable=False
    )
    op.drop_constraint("channelseasonfilter_pkey", "channelseasonfilter", type_="primary")
    op.drop_column("channelseasonfilter", "season_identifier")
    op.create_primary_key(
        "channelseasonwhitelist_pkey",
        "channelseasonfilter",
        ["channel_show_id", "season_id"],
    )
    op.create_index(
        "ChannelSeasonFilter-season_id-index", "channelseasonfilter", ["season_id"]
    )
    op.create_foreign_key(
        "channelseasonfilter_season_id_fkey",
        "channelseasonfilter",
        "season",
        ["season_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column(
        "channelepisodefilter", sa.Column("episode_id", sa.Uuid(), nullable=True)
    )
    op.execute(
        """
        UPDATE channelepisodefilter
        SET episode_id = chosen.id
        FROM (
            SELECT DISTINCT ON (episode_identifier) episode_identifier, id
            FROM episode
            WHERE deleted_at IS NULL
            ORDER BY episode_identifier, created_at, id
        ) AS chosen
        WHERE chosen.episode_identifier = channelepisodefilter.episode_identifier
        """
    )
    op.execute("DELETE FROM channelepisodefilter WHERE episode_id IS NULL")
    op.alter_column(
        "channelepisodefilter", "episode_id", existing_type=sa.Uuid(), nullable=False
    )
    op.drop_constraint(
        "channelepisodefilter_pkey", "channelepisodefilter", type_="primary"
    )
    op.drop_column("channelepisodefilter", "episode_identifier")
    op.create_primary_key(
        "channelepisodewhitelist_pkey",
        "channelepisodefilter",
        ["channel_show_id", "episode_id"],
    )
    op.create_index(
        "ChannelEpisodeFilter-episode_id-index", "channelepisodefilter", ["episode_id"]
    )
    op.create_foreign_key(
        "channelepisodefilter_episode_id_fkey",
        "channelepisodefilter",
        "episode",
        ["episode_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index("ChannelSourceFilter-show_id-index", table_name="channelsourcefilter")
    op.drop_table("channelsourcefilter")
