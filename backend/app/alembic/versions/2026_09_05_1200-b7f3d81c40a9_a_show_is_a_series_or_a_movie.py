# TODO: Validate
from alembic import op

revision = "b7f3d81c40a9"
down_revision = "c4b1e97f3d20"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.execute(
        """
        UPDATE show
        SET media_type = 'Series'
        WHERE media_type IN ('TV Show', 'TV Series')
        """,
    )


# TODO: Validate
def downgrade() -> None:
    op.execute(
        """
        UPDATE show
        SET media_type = 'TV Show'
        WHERE media_type = 'Series'
        """,
    )
