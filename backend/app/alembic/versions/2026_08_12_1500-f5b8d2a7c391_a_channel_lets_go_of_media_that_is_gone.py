"""a channel lets go of media that is gone

The four pointers a channel holds at canonical media refused the deletion of the
row they name. That rule was written when a canonical row was its own table and
nothing ever deleted one; now that a copy and the media it is of share a table,
deleting a title is ordinary work and the refusal only leaves the delete to fail.

They cascade instead. A channel row that names a title which no longer exists
says nothing, so it goes with it, and the filters hanging off a `ChannelShow`
follow by the cascade they already had.

Revision ID: f5b8d2a7c391
Revises: e4a9c1f6b285
Create Date: 2026-08-12 15:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f5b8d2a7c391"
down_revision = "e4a9c1f6b285"
branch_labels = None
depends_on = None

# What a channel holds, and the table each of them names.
_CHANNEL_POINTERS = (
    ("channelshow", "canonical_show_id", "channelshow_canonical_show_id_fkey", "show"),
    (
        "channelseasonfilter",
        "canonical_season_id",
        "channelseasonfilter_canonical_season_id_fkey",
        "season",
    ),
    (
        "channelepisodefilter",
        "canonical_episode_id",
        "channelepisodefilter_canonical_episode_id_fkey",
        "episode",
    ),
    (
        "channelsavedepisodeorder",
        "canonical_episode_id",
        "channelsavedepisodeorder_canonical_episode_id_fkey",
        "episode",
    ),
)


def _repoint(ondelete: str) -> None:
    for table, column, name, target in _CHANNEL_POINTERS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(
            name,
            table,
            target,
            [column],
            ["id"],
            ondelete=ondelete,
        )


def upgrade() -> None:
    _repoint("CASCADE")


def downgrade() -> None:
    _repoint("RESTRICT")
