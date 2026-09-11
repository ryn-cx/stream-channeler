# TODO: Validate
from alembic import op

revision = "f4b93c208d71"
down_revision = "d7c2f81a4b60"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.execute(
        """
        DELETE FROM file
        WHERE left(key, 10) = 'TitlePage/'
        AND plugin_id IN (SELECT id FROM plugin WHERE key = 'Adult Swim')
        """,
    )


# TODO: Validate
def downgrade() -> None:
    pass
