import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "c7e2a53bd841"
down_revision = "b6d1f49ac730"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "userepisodeurl",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_episode_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["canonical_episode_id"],
            ["episode.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "canonical_episode_id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(
        "UserEpisodeUrl-canonical_episode_id-index",
        "userepisodeurl",
        ["canonical_episode_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "UserEpisodeUrl-canonical_episode_id-index",
        table_name="userepisodeurl",
    )
    op.drop_table("userepisodeurl")
