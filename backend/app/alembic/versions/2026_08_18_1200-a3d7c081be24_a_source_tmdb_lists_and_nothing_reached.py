"""a source tmdb lists and nothing reached

TMDB names every service carrying a title, Watchmode names most of them by a
link, and the two do not agree. A service Watchmode gave no address for is
looked for by searching that service, and one the search does not reach either
is left with nowhere to import from at all.

That leftover is written down here, a row to the service, so an admin can supply
the address by hand rather than the listing being lost. A row is dropped as soon
as the title is imported from that service, whether by hand or by a later import
reaching it.

Revision ID: a3d7c081be24
Revises: f6c9a4e37b25
Create Date: 2026-08-18 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = "a3d7c081be24"
down_revision = "f6c9a4e37b25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "unmatchedsource",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "provider_name",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
        ),
        sa.Column(
            "plugin_key",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("show_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["show_id"], ["show.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint(
            "show_id",
            "provider_name",
            name="UnmatchedSource-show_id-provider_name-unique",
        ),
    )
    op.create_index(
        "UnmatchedSource-show_id-index",
        "unmatchedsource",
        ["show_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("UnmatchedSource-show_id-index", table_name="unmatchedsource")
    op.drop_table("unmatchedsource")
