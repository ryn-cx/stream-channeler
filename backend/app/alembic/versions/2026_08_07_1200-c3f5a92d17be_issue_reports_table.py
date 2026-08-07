"""move issue reports into a table per media type

Revision ID: c3f5a92d17be
Revises: b7d4e18c05fa
Create Date: 2026-08-07 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "c3f5a92d17be"
down_revision = "b7d4e18c05fa"
branch_labels = None
depends_on = None

MEDIA_TABLES = ("episode", "season", "show")


def _table_name(media_table):
    return f"{media_table}issuereport"


def _index_prefix(media_table):
    return f"{media_table.capitalize()}IssueReport"


def upgrade():
    for media_table in MEDIA_TABLES:
        table = _table_name(media_table)
        media_column = f"{media_table}_id"
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("report", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=True),
            sa.Column(media_column, sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                [media_column],
                [f"{media_table}.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("id"),
        )
        op.create_index(
            f"{_index_prefix(media_table)}-{media_column}-index",
            table,
            [media_column],
        )
        op.create_index(
            f"{_index_prefix(media_table)}-user_id-index",
            table,
            ["user_id"],
        )

    # The old column recorded no author, so what was already reported is carried
    # over as a report nobody is named on, which is the same shape a report left
    # by a visitor with no account takes.
    op.execute(
        """
        INSERT INTO episodeissuereport (
            id, created_at, modified_at, report, user_id, episode_id
        )
        SELECT gen_random_uuid(), now(), now(), issue_report, NULL, id
        FROM episode
        WHERE issue_report IS NOT NULL
        """,
    )
    op.drop_column("episode", "issue_report")


def downgrade():
    op.add_column(
        "episode",
        sa.Column("issue_report", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.execute(
        """
        UPDATE episode
        SET issue_report = episodeissuereport.report
        FROM episodeissuereport
        WHERE episodeissuereport.episode_id = episode.id
        """,
    )
    for media_table in MEDIA_TABLES:
        table = _table_name(media_table)
        op.drop_index(f"{_index_prefix(media_table)}-user_id-index", table_name=table)
        op.drop_index(
            f"{_index_prefix(media_table)}-{media_table}_id-index",
            table_name=table,
        )
        op.drop_table(table)
