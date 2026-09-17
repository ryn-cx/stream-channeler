import sqlalchemy as sa
from alembic import op

revision = "b83f5c1d97ae"
down_revision = "f1a4d29e6b53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("title", sa.Column("poster_url", sa.String(), nullable=True))
    op.create_table(
        "watchprovider",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tmdb_provider_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("logo_url", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint(
            "tmdb_provider_id",
            name="WatchProvider-tmdb_provider_id-unique",
        ),
    )
    op.create_table(
        "titlewatchprovider",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title_id", sa.Uuid(), nullable=False),
        sa.Column("watch_provider_id", sa.Uuid(), nullable=False),
        sa.Column("region", sa.String(length=2), nullable=False),
        sa.Column("offering_type", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["title_id"], ["title.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["watch_provider_id"],
            ["watchprovider.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "title_id",
            "region",
            "watch_provider_id",
            "offering_type",
        ),
        sa.UniqueConstraint("id"),
    )
    op.create_index(
        "TitleWatchProvider-region-watch_provider_id-index",
        "titlewatchprovider",
        ["region", "watch_provider_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "TitleWatchProvider-region-watch_provider_id-index",
        table_name="titlewatchprovider",
    )
    op.drop_table("titlewatchprovider")
    op.drop_table("watchprovider")
    op.drop_column("title", "poster_url")
