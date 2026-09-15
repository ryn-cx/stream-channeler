import sqlalchemy as sa
from alembic import op

revision = "d3a6f19b8c47"
down_revision = "b7f3d81c40a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "channel",
        sa.Column("update_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE channel
        SET update_at = NOW()
        FROM "user"
        WHERE "user".id = channel.user_id
        AND "user".email ILIKE '%@StreamChanneler.Com'
        """,
    )


def downgrade() -> None:
    op.drop_column("channel", "update_at")
