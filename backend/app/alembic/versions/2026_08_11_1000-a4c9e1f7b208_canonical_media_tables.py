"""separate the media being filtered from where it can be watched

A `Show`, `Season` and `Episode` are one website's copy of something, and until
now they were also the something itself: a magic identifier string on each row
both grouped the copies and, when it was shaped like `TMDB <type> <id>`, stood
in for the TMDB record. Nothing in the database held either job to account.

The canonical tables created here are the media itself. A TMDB identity is an
optional column pair on them rather than the reason a row exists, so a title
TMDB lists and a YouTube channel's uploads are both rows in the same table and
are filtered by the same query. The copies keep their identifiers for now and
gain a nullable pointer at the canonical row; a later revision backfills it,
makes it required, and drops the identifiers.

Revision ID: a4c9e1f7b208
Revises: d18c5f37ba62
Create Date: 2026-08-11 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "a4c9e1f7b208"
down_revision = "d18c5f37ba62"
branch_labels = None
depends_on = None


# The copy table, the column pointing at its canonical row, and the canonical
# table it points at.
COPY_LINKS = (
    ("show", "canonical_show_id", "canonicalshow", "Show"),
    ("season", "canonical_season_id", "canonicalseason", "Season"),
    ("episode", "canonical_episode_id", "canonicalepisode", "Episode"),
)


def upgrade():
    op.create_table(
        "canonicalshow",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "tmdb_media_type",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("media_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("image_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("icon", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        # Postgres counts NULLs as distinct, so this binds every TMDB title to
        # one row while leaving titles TMDB has no entry for free to be as many
        # rows as there are of them.
        sa.UniqueConstraint(
            "tmdb_media_type",
            "tmdb_id",
            name="CanonicalShow-tmdb_media_type-tmdb_id-key",
        ),
        sa.CheckConstraint(
            "(tmdb_media_type IS NULL) = (tmdb_id IS NULL)",
            name="CanonicalShow-tmdb-identity-complete",
        ),
    )
    op.create_index("CanonicalShow-media_type-index", "canonicalshow", ["media_type"])
    op.create_index("CanonicalShow-name-index", "canonicalshow", ["name"])
    op.create_index("CanonicalShow-tmdb_id-index", "canonicalshow", ["tmdb_id"])

    op.create_table(
        "canonicalseason",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canonical_show_id", sa.Uuid(), nullable=False),
        sa.Column(
            "tmdb_media_type",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("image_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["canonical_show_id"],
            ["canonicalshow.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint(
            "tmdb_media_type",
            "tmdb_id",
            name="CanonicalSeason-tmdb_media_type-tmdb_id-key",
        ),
        sa.CheckConstraint(
            "(tmdb_media_type IS NULL) = (tmdb_id IS NULL)",
            name="CanonicalSeason-tmdb-identity-complete",
        ),
    )
    op.create_index(
        "CanonicalSeason-canonical_show_id-index",
        "canonicalseason",
        ["canonical_show_id"],
    )
    op.create_index("CanonicalSeason-name-index", "canonicalseason", ["name"])
    op.create_index(
        "CanonicalSeason-season_number-index",
        "canonicalseason",
        ["season_number"],
    )
    op.create_index(
        "CanonicalSeason-sort_order-index",
        "canonicalseason",
        ["sort_order"],
    )

    op.create_table(
        "canonicalepisode",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canonical_season_id", sa.Uuid(), nullable=False),
        sa.Column(
            "tmdb_media_type",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("image_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("episode_number", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("air_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["canonical_season_id"],
            ["canonicalseason.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint(
            "tmdb_media_type",
            "tmdb_id",
            name="CanonicalEpisode-tmdb_media_type-tmdb_id-key",
        ),
        sa.CheckConstraint(
            "(tmdb_media_type IS NULL) = (tmdb_id IS NULL)",
            name="CanonicalEpisode-tmdb-identity-complete",
        ),
    )
    op.create_index(
        "CanonicalEpisode-canonical_season_id-index",
        "canonicalepisode",
        ["canonical_season_id"],
    )
    for field in (
        "air_date",
        "duration",
        "episode_number",
        "name",
        "release_date",
        "sort_order",
    ):
        op.create_index(
            f"CanonicalEpisode-{field}-index",
            "canonicalepisode",
            [field],
        )

    # RESTRICT rather than CASCADE: a canonical row outlives every copy of it,
    # because a `Watch` records what was watched rather than where.
    for copy_table, column, canonical_table, index_prefix in COPY_LINKS:
        op.add_column(copy_table, sa.Column(column, sa.Uuid(), nullable=True))
        op.create_foreign_key(
            f"{copy_table}_{column}_fkey",
            copy_table,
            canonical_table,
            [column],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"{index_prefix}-{column}-index", copy_table, [column])


def downgrade():
    for copy_table, column, _canonical_table, index_prefix in COPY_LINKS:
        op.drop_index(f"{index_prefix}-{column}-index", table_name=copy_table)
        op.drop_constraint(
            f"{copy_table}_{column}_fkey", copy_table, type_="foreignkey"
        )
        op.drop_column(copy_table, column)

    op.drop_table("canonicalepisode")
    op.drop_table("canonicalseason")
    op.drop_table("canonicalshow")
