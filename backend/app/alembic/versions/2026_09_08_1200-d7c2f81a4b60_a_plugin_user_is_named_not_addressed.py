# TODO: Validate
from alembic import op

revision = "d7c2f81a4b60"
down_revision = "e3a71b5c48d9"
branch_labels = None
depends_on = None


# TODO: Validate
def upgrade() -> None:
    op.execute(
        """
        UPDATE "user"
        SET email = split_part(email, '@', 1)
        WHERE email ILIKE '%@StreamChanneler.Com'
        """,
    )


# TODO: Validate
def downgrade() -> None:
    op.execute(
        """
        UPDATE "user"
        SET email = email || '@StreamChanneler.Com'
        WHERE email NOT LIKE '%@%'
        """,
    )
