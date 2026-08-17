"""an episode stands for however many episodes

A website's row named the one episode it stood for in a column, which said that a
listing is a listing of one episode. It is not: a website runs two episodes
together in one listing - a double-length first airing, a recap paired with the
episode it recaps - and the row stands for each of them as much as for the other,
which a column can only hold one of.

`EpisodeCanonicalEpisode` becomes the whole of that record, the way
`ShowCanonicalShow` already is for titles, and `episode.is_canonical` takes over
saying which kind of row this is. Every link the column held becomes a row there.

Where a copy sits moves onto the link with it. A row stands in a different place
under each episode it was linked to, so the place belongs to the link; the
column stays for the episodes themselves, which are ordered by their own, and for
a row nothing has linked yet to fall back on.

Revision ID: f6c9a4e37b25
Revises: e5b8d3f26a94
Create Date: 2026-08-16 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6c9a4e37b25"
down_revision = "e5b8d3f26a94"
branch_labels = None
depends_on = None

# The indexes that order the episodes themselves, which said which rows those
# were by the column being dropped and now say it by the flag.
_CANONICAL_SORTABLE_FIELDS = (
    "air_date",
    "duration",
    "episode_number",
    "name",
    "sort_order",
)


def upgrade() -> None:
    op.create_table(
        "episodecanonicalepisode",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("episode_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_episode_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["episode.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_episode_id"],
            ["episode.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("episode_id", "canonical_episode_id"),
    )
    op.create_index(
        "EpisodeCanonicalEpisode-canonical_episode_id-index",
        "episodecanonicalepisode",
        ["canonical_episode_id"],
    )

    # Every link the column held, with the place the copy was filed under carried
    # onto the link that now holds it.
    op.execute(
        """
        INSERT INTO episodecanonicalepisode (
            id, created_at, modified_at, episode_id, canonical_episode_id, sort_order
        )
        SELECT
            gen_random_uuid(),
            now(),
            now(),
            id,
            canonical_episode_id,
            sort_order
        FROM episode
        WHERE canonical_episode_id IS NOT NULL
        """,
    )

    op.add_column(
        "episode",
        sa.Column(
            "is_canonical",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute(
        "UPDATE episode SET is_canonical = false WHERE canonical_episode_id IS NOT NULL",
    )
    op.alter_column("episode", "is_canonical", server_default=None)

    op.drop_index("Episode-canonical_episode_id-index", table_name="episode")
    op.drop_index(
        "Episode-live-season_id-canonical_episode_id-key",
        table_name="episode",
    )
    op.drop_index("Episode-canonical-key-index", table_name="episode")
    for field in _CANONICAL_SORTABLE_FIELDS:
        op.drop_index(f"Episode-{field}-index", table_name="episode")

    op.drop_column("episode", "canonical_episode_id")

    op.create_index("Episode-is_canonical-index", "episode", ["is_canonical"])
    op.execute(
        'CREATE INDEX "Episode-canonical-key-index"'
        " ON episode (key) WHERE is_canonical IS TRUE",
    )
    for field in _CANONICAL_SORTABLE_FIELDS:
        op.execute(
            f'CREATE INDEX "Episode-{field}-index"'
            f" ON episode ({field}) WHERE is_canonical IS TRUE",
        )


def downgrade() -> None:
    op.add_column("episode", sa.Column("canonical_episode_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "episode_canonical_episode_id_fkey",
        "episode",
        "episode",
        ["canonical_episode_id"],
        ["id"],
    )
    # A row standing for more than one keeps whichever link was written first,
    # which is the most a column can be given back.
    op.execute(
        """
        UPDATE episode
        SET canonical_episode_id = first_link.canonical_episode_id
        FROM (
            SELECT DISTINCT ON (episode_id) episode_id, canonical_episode_id, sort_order
            FROM episodecanonicalepisode
            ORDER BY episode_id, created_at
        ) AS first_link
        WHERE episode.id = first_link.episode_id
        """,
    )

    op.drop_index("Episode-is_canonical-index", table_name="episode")
    op.drop_index("Episode-canonical-key-index", table_name="episode")
    for field in _CANONICAL_SORTABLE_FIELDS:
        op.drop_index(f"Episode-{field}-index", table_name="episode")

    op.drop_column("episode", "is_canonical")

    op.create_index(
        "Episode-canonical_episode_id-index",
        "episode",
        ["canonical_episode_id"],
    )
    op.execute(
        'CREATE INDEX "Episode-live-season_id-canonical_episode_id-key"'
        " ON episode (season_id, canonical_episode_id)"
        " WHERE deleted_at IS NULL AND canonical_episode_id IS NOT NULL",
    )
    op.execute(
        'CREATE INDEX "Episode-canonical-key-index"'
        " ON episode (key) WHERE canonical_episode_id IS NULL",
    )
    for field in _CANONICAL_SORTABLE_FIELDS:
        op.execute(
            f'CREATE INDEX "Episode-{field}-index"'
            f" ON episode ({field}) WHERE canonical_episode_id IS NULL",
        )

    op.drop_index(
        "EpisodeCanonicalEpisode-canonical_episode_id-index",
        table_name="episodecanonicalepisode",
    )
    op.drop_table("episodecanonicalepisode")
