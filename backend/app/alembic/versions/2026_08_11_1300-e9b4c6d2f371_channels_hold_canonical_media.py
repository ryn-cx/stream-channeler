"""hold canonical media on a channel rather than an identifier string

A channel held a title by the string every copy of it carries, and its filters
named a season and an episode the same way. The canonical rows are what those
strings stood for, so the channel now points at them and the strings go.

`ChannelSourceFilter` is deliberately untouched: it says which websites' copies
of a title a `User` wants, which is the one thing here that really is about
where rather than what.

A row naming an identifier no media carries any more resolves to nothing and is
dropped. It could not have matched anything either way -- the join it took part
in was against the same identifier -- so what goes is a row that was already
inert. That makes this irreversible, as does collapsing a saved order that held
two copies of one episode.

Revision ID: e9b4c6d2f371
Revises: d7f3b2a8c159
Create Date: 2026-08-11 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e9b4c6d2f371"
down_revision = "d7f3b2a8c159"
branch_labels = None
depends_on = None

# Each level's filter table, the identifier it was keyed on, and the copy table
# holding the mapping from that identifier to the canonical row.
LEVELS = (
    ("channelshow", "show_identifier", "canonical_show_id", "show", "canonicalshow"),
    (
        "channelseasonfilter",
        "season_identifier",
        "canonical_season_id",
        "season",
        "canonicalseason",
    ),
    (
        "channelepisodefilter",
        "episode_identifier",
        "canonical_episode_id",
        "episode",
        "canonicalepisode",
    ),
)


def _repoint(table, identifier, canonical, copy_table):
    """Give `table` the canonical row its identifier stands for, dropping the rest."""
    op.add_column(table, sa.Column(canonical, sa.Uuid(), nullable=True))
    # DISTINCT ON only to make the join one-to-one: every copy sharing an
    # identifier was given the same canonical row by revision b6d2f4a9c317.
    # Soft-deleted copies count, so a title a `User` still has on a channel is
    # not dropped for having been removed from the library.
    op.execute(
        f"""
        UPDATE {table} SET {canonical} = resolved.{canonical}
        FROM (
            SELECT DISTINCT ON ({identifier}) {identifier}, {canonical}
            FROM {copy_table}
            WHERE {canonical} IS NOT NULL
            ORDER BY {identifier}, id
        ) AS resolved
        WHERE resolved.{identifier} = {table}.{identifier}
        """,  # noqa: S608 - Built from the constants above, never from stored data.
    )
    op.execute(f"DELETE FROM {table} WHERE {canonical} IS NULL")  # noqa: S608
    op.alter_column(table, canonical, existing_type=sa.Uuid(), nullable=False)


def upgrade():
    for table, identifier, canonical, copy_table, canonical_table in LEVELS:
        _repoint(table, identifier, canonical, copy_table)
        # RESTRICT: a canonical row a channel holds is one nothing may delete.
        op.create_foreign_key(
            f"{table}_{canonical}_fkey",
            table,
            canonical_table,
            [canonical],
            ["id"],
            ondelete="RESTRICT",
        )

    op.drop_constraint("channelshow_pkey", "channelshow", type_="primary")
    op.drop_index("ChannelShow-show_identifier-index", table_name="channelshow")
    op.drop_column("channelshow", "show_identifier")
    op.create_primary_key(
        "channelshow_pkey",
        "channelshow",
        ["channel_id", "canonical_show_id"],
    )
    op.create_index(
        "ChannelShow-canonical_show_id-index",
        "channelshow",
        ["canonical_show_id"],
    )

    op.drop_constraint(
        "channelseasonfilter_pkey", "channelseasonfilter", type_="primary"
    )
    op.drop_column("channelseasonfilter", "season_identifier")
    op.create_primary_key(
        "channelseasonfilter_pkey",
        "channelseasonfilter",
        ["channel_show_id", "canonical_season_id"],
    )
    op.create_index(
        "ChannelSeasonFilter-canonical_season_id-index",
        "channelseasonfilter",
        ["canonical_season_id"],
    )

    op.drop_constraint(
        "channelepisodefilter_pkey",
        "channelepisodefilter",
        type_="primary",
    )
    op.drop_column("channelepisodefilter", "episode_identifier")
    op.create_primary_key(
        "channelepisodefilter_pkey",
        "channelepisodefilter",
        ["channel_show_id", "canonical_episode_id"],
    )
    op.create_index(
        "ChannelEpisodeFilter-canonical_episode_id-index",
        "channelepisodefilter",
        ["canonical_episode_id"],
    )

    # The saved order was keyed on one website's copy, so a channel offering the
    # same episode from two websites could hold a position for each. They are one
    # episode to order, and the earlier position is the one the `User` put it at.
    op.add_column(
        "channelsavedepisodeorder",
        sa.Column("canonical_episode_id", sa.Uuid(), nullable=True),
    )
    op.execute(
        """
        UPDATE channelsavedepisodeorder
        SET canonical_episode_id = episode.canonical_episode_id
        FROM episode
        WHERE episode.id = channelsavedepisodeorder.episode_id
        """,
    )
    op.execute(
        "DELETE FROM channelsavedepisodeorder WHERE canonical_episode_id IS NULL"
    )
    op.execute(
        """
        DELETE FROM channelsavedepisodeorder AS duplicate
        USING channelsavedepisodeorder AS kept
        WHERE duplicate.channel_id = kept.channel_id
          AND duplicate.canonical_episode_id = kept.canonical_episode_id
          AND (duplicate.position, duplicate.ctid) > (kept.position, kept.ctid)
        """,
    )
    op.alter_column(
        "channelsavedepisodeorder",
        "canonical_episode_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_foreign_key(
        "channelsavedepisodeorder_canonical_episode_id_fkey",
        "channelsavedepisodeorder",
        "canonicalepisode",
        ["canonical_episode_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "channelsavedepisodeorder_pkey",
        "channelsavedepisodeorder",
        type_="primary",
    )
    op.drop_index(
        "ChannelSavedEpisodeOrder-episode_id-index",
        table_name="channelsavedepisodeorder",
    )
    op.drop_column("channelsavedepisodeorder", "episode_id")
    op.create_primary_key(
        "channelsavedepisodeorder_pkey",
        "channelsavedepisodeorder",
        ["channel_id", "canonical_episode_id"],
    )
    op.create_index(
        "ChannelSavedEpisodeOrder-canonical_episode_id-index",
        "channelsavedepisodeorder",
        ["canonical_episode_id"],
    )


def _restore_identifier(table, identifier, canonical, copy_table):
    """Put back the identifier the canonical row stands for."""
    op.add_column(table, sa.Column(identifier, sa.String(), nullable=True))
    op.execute(
        f"""
        UPDATE {table} SET {identifier} = resolved.{identifier}
        FROM (
            SELECT DISTINCT ON ({canonical}) {canonical}, {identifier}
            FROM {copy_table}
            WHERE {canonical} IS NOT NULL
            ORDER BY {canonical}, id
        ) AS resolved
        WHERE resolved.{canonical} = {table}.{canonical}
        """,  # noqa: S608 - Built from the constants above, never from stored data.
    )
    op.execute(f"DELETE FROM {table} WHERE {identifier} IS NULL")  # noqa: S608
    op.alter_column(table, identifier, existing_type=sa.String(), nullable=False)


def downgrade():
    op.drop_index(
        "ChannelSavedEpisodeOrder-canonical_episode_id-index",
        table_name="channelsavedepisodeorder",
    )
    op.drop_constraint(
        "channelsavedepisodeorder_pkey",
        "channelsavedepisodeorder",
        type_="primary",
    )
    op.add_column(
        "channelsavedepisodeorder",
        sa.Column("episode_id", sa.Uuid(), nullable=True),
    )
    # A canonical episode goes back to one copy of itself, since the copies it
    # was collapsed from cannot be told apart any more.
    op.execute(
        """
        UPDATE channelsavedepisodeorder
        SET episode_id = chosen.id
        FROM (
            SELECT DISTINCT ON (canonical_episode_id) canonical_episode_id, id
            FROM episode
            WHERE canonical_episode_id IS NOT NULL AND deleted_at IS NULL
            ORDER BY canonical_episode_id, created_at, id
        ) AS chosen
        WHERE chosen.canonical_episode_id = channelsavedepisodeorder.canonical_episode_id
        """,
    )
    op.execute("DELETE FROM channelsavedepisodeorder WHERE episode_id IS NULL")
    op.alter_column(
        "channelsavedepisodeorder",
        "episode_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_constraint(
        "channelsavedepisodeorder_canonical_episode_id_fkey",
        "channelsavedepisodeorder",
        type_="foreignkey",
    )
    op.drop_column("channelsavedepisodeorder", "canonical_episode_id")
    op.create_primary_key(
        "channelsavedepisodeorder_pkey",
        "channelsavedepisodeorder",
        ["channel_id", "episode_id"],
    )
    op.create_index(
        "ChannelSavedEpisodeOrder-episode_id-index",
        "channelsavedepisodeorder",
        ["episode_id"],
    )

    for table, identifier, canonical, copy_table, _canonical_table in reversed(LEVELS):
        op.drop_constraint(f"{table}_{canonical}_fkey", table, type_="foreignkey")
        _restore_identifier(table, identifier, canonical, copy_table)

    op.drop_index(
        "ChannelEpisodeFilter-canonical_episode_id-index",
        table_name="channelepisodefilter",
    )
    op.drop_constraint(
        "channelepisodefilter_pkey",
        "channelepisodefilter",
        type_="primary",
    )
    op.drop_column("channelepisodefilter", "canonical_episode_id")
    op.create_primary_key(
        "channelepisodefilter_pkey",
        "channelepisodefilter",
        ["channel_show_id", "episode_identifier"],
    )

    op.drop_index(
        "ChannelSeasonFilter-canonical_season_id-index",
        table_name="channelseasonfilter",
    )
    op.drop_constraint(
        "channelseasonfilter_pkey", "channelseasonfilter", type_="primary"
    )
    op.drop_column("channelseasonfilter", "canonical_season_id")
    op.create_primary_key(
        "channelseasonfilter_pkey",
        "channelseasonfilter",
        ["channel_show_id", "season_identifier"],
    )

    op.drop_index("ChannelShow-canonical_show_id-index", table_name="channelshow")
    op.drop_constraint("channelshow_pkey", "channelshow", type_="primary")
    op.drop_column("channelshow", "canonical_show_id")
    op.create_primary_key(
        "channelshow_pkey",
        "channelshow",
        ["channel_id", "show_identifier"],
    )
    op.create_index(
        "ChannelShow-show_identifier-index",
        "channelshow",
        ["show_identifier"],
    )
