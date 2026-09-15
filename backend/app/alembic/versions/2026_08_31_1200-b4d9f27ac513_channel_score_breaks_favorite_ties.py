import sqlalchemy as sa
from alembic import op

revision = "b4d9f27ac513"
down_revision = "a1e7c53d9f24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "channel",
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("channel", "score", server_default=None)
    op.execute(
        """
        UPDATE channel
        SET score = -1
        FROM "user"
        WHERE "user".id = channel.user_id
        AND "user".email = 'plugins@streamchanneler.com'
        """,
    )


def downgrade() -> None:
    op.drop_column("channel", "score")
