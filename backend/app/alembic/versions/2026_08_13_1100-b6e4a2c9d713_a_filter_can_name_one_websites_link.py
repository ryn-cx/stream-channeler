"""a filter can name one website's link

Taking an episode out of a channel took it out everywhere: a `channelepisodefilter`
row names the canonical episode, which every website carrying the show shares, so
there was no way to drop a site's bad rip of one episode and keep the rest of that
site's links.

`channelepisodesourcefilter` is that exception. It names the canonical episode the
way the plain filter does and the linked show alongside it, so it covers one
website's link to the episode and leaves every other website's alone. Nothing is
migrated into it: it says something no existing row could say.

Revision ID: b6e4a2c9d713
Revises: a5c3e8b1d740
Create Date: 2026-08-13 11:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b6e4a2c9d713"
down_revision = "a5c3e8b1d740"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channelepisodesourcefilter",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel_show_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_episode_id", sa.Uuid(), nullable=False),
        sa.Column("show_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["channel_show_id"],
            ["channelshow.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_episode_id"],
            ["episode.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["show_id"], ["show.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("channel_show_id", "canonical_episode_id", "show_id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(
        "ChannelEpisodeSourceFilter-canonical_episode_id-index",
        "channelepisodesourcefilter",
        ["canonical_episode_id"],
    )
    op.create_index(
        "ChannelEpisodeSourceFilter-show_id-index",
        "channelepisodesourcefilter",
        ["show_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ChannelEpisodeSourceFilter-show_id-index",
        table_name="channelepisodesourcefilter",
    )
    op.drop_index(
        "ChannelEpisodeSourceFilter-canonical_episode_id-index",
        table_name="channelepisodesourcefilter",
    )
    op.drop_table("channelepisodesourcefilter")
